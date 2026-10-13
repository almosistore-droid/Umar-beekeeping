"""Permanent hive QR codes: payload `hive_<uuid>` inside a Telegram Mini App deep link.

The payload depends only on the hive UUID, so number, queen, family, health or apiary changes
never break a printed label.
"""
import base64
import io
import re
import uuid

import segno
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import CAN_MANAGE
from app.config import get_settings
from app.models import ARCHIVED_HIVE_STATUSES, Hive, QrCode, User
from app.schemas.qr import QrOut, QrResolveOut

PREFIX = "hive_"
_UUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
_PAYLOAD_RE = re.compile(rf"{PREFIX}({_UUID})", re.IGNORECASE)
_PATH_RE = re.compile(rf"/hives/({_UUID})(?:[/?#]|$)", re.IGNORECASE)
_BARE_RE = re.compile(rf"^{_UUID}$")


def payload(hive_id: uuid.UUID) -> str:
    return f"{PREFIX}{hive_id}"


def deep_link(code: str) -> str | None:
    """t.me link that opens the Mini App with start_param=code, or None if the bot is not configured."""
    s = get_settings()
    bot = s.telegram_bot_username.strip().lstrip("@")
    if not bot:
        return None
    app_name = s.telegram_webapp_short_name.strip()
    if app_name:
        return f"https://t.me/{bot}/{app_name}?startapp={code}"
    # Main Mini App of the bot (BotFather → Bot Settings → Configure Mini App)
    return f"https://t.me/{bot}?startapp={code}"


def qr_content(code: str) -> str:
    return deep_link(code) or code


def parse(text: str | None) -> uuid.UUID | None:
    """Hive UUID from anything a scanner may return: t.me link, startapp payload, app URL, bare UUID."""
    if not text:
        return None
    text = text.strip()[:2048]
    for rx in (_PAYLOAD_RE, _PATH_RE):
        m = rx.search(text)
        if m:
            return uuid.UUID(m.group(1))
    if _BARE_RE.match(text):
        return uuid.UUID(text)
    return None


def svg_data_uri(content: str) -> str:
    """Standalone SVG (with xmlns, so it renders in an <img>) as a data URI."""
    buf = io.BytesIO()
    segno.make(content, error="m").save(buf, kind="svg", scale=8, border=2, dark="#15120c", light="#ffffff",
                                         xmldecl=False, svgns=True)
    return "data:image/svg+xml;base64," + base64.b64encode(buf.getvalue()).decode()


def find(db: Session, hive_id: uuid.UUID) -> QrCode | None:
    return db.scalar(select(QrCode).where(QrCode.hive_id == hive_id))


def ensure(db: Session, hive: Hive, user: User | None) -> QrCode:
    """Create the hive's QR if it does not exist yet. Never changes an existing code. Flushes only."""
    qr = find(db, hive.id)
    if qr is None:
        qr = QrCode(hive_id=hive.id, code=payload(hive.id), created_by_id=user.id if user else None)
        db.add(qr)
        db.flush()
    return qr


def to_out(hive: Hive, qr: QrCode) -> QrOut:
    link = deep_link(qr.code)
    content = link or qr.code
    return QrOut(
        hive_id=hive.id, hive_number=hive.hive_number, apiary_name=hive.apiary.name, code=qr.code,
        deep_link=link, content=content, deep_link_ready=link is not None, svg_data_uri=svg_data_uri(content),
        print_count=qr.print_count, last_printed_at=qr.last_printed_at,
    )


def resolve(db: Session, text: str | None, user: User) -> QrResolveOut:
    hive_id = parse(text)
    if hive_id is None:
        return QrResolveOut(status="invalid")
    hive = db.get(Hive, hive_id)
    if hive is None:
        return QrResolveOut(status="unknown", hive_id=hive_id, can_register=user.role in CAN_MANAGE)
    return QrResolveOut(
        status="found", hive_id=hive.id, hive_number=hive.hive_number, apiary_name=hive.apiary.name,
        is_archived=hive.status in ARCHIVED_HIVE_STATUSES,
    )
