"""Printable A4 sheet of hive QR labels (3 × 4 per page, dashed cut lines)."""
import io
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import segno
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.i18n import L
from app.models import ARCHIVED_HIVE_STATUSES, Hive, User
from app.repositories.hive_repository import natural_order
from app.schemas.qr import LabelsRequest, MAX_LABEL_HIVES
from app.services import audit_service as audit
from app.services import qr_service
from app.services.apiary_service import get_apiary
from app.utils.errors import NotFoundError, ValidationFailed

FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
COLS, ROWS = 3, 4
INK = HexColor("#15120c")
MUTED = HexColor("#6b6458")
CUT = HexColor("#c8c2b6")


@dataclass
class Label:
    content: str
    title: str
    subtitle: str


def _register_fonts() -> None:
    if "DejaVu" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("DejaVu", str(FONTS / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(FONTS / "DejaVuSans-Bold.ttf")))


def _fit(c: Canvas, text: str, font: str, size: float, width: float) -> str:
    while text and c.stringWidth(text, font, size) > width:
        text = text[:-2] + "…" if len(text) > 2 else ""
    return text


def _draw_qr(c: Canvas, content: str, x: float, y: float, size: float) -> None:
    rows = [list(r) for r in segno.make(content, error="m").matrix_iter(scale=1, border=0)]
    module = size / len(rows)
    c.setFillColor(INK)
    for i, row in enumerate(rows):
        j = 0
        while j < len(row):  # merge runs of dark modules into one rectangle
            if row[j]:
                start = j
                while j < len(row) and row[j]:
                    j += 1
                c.rect(x + start * module, y + size - (i + 1) * module, (j - start) * module, module, stroke=0, fill=1)
            else:
                j += 1


def render(labels: list[Label]) -> bytes:
    _register_fonts()
    buf = io.BytesIO()
    c = Canvas(buf, pagesize=A4)
    c.setTitle(L("QR-наклейки ульев"))
    c.setAuthor("Fayzi Umar")
    page_w, page_h = A4
    cell_w, cell_h = page_w / COLS, page_h / ROWS
    qr_size = 50 * mm
    for index, label in enumerate(labels):
        pos = index % (COLS * ROWS)
        if index and pos == 0:
            c.showPage()
        if pos == 0:  # dashed cut lines
            c.setStrokeColor(CUT)
            c.setLineWidth(0.4)
            c.setDash(2, 3)
            for k in range(1, COLS):
                c.line(k * cell_w, 0, k * cell_w, page_h)
            for k in range(1, ROWS):
                c.line(0, k * cell_h, page_w, k * cell_h)
            c.setDash()
        col, row = pos % COLS, pos // COLS
        x0, top = col * cell_w, page_h - row * cell_h
        cx = x0 + cell_w / 2
        qr_bottom = top - 5 * mm - qr_size
        _draw_qr(c, label.content, cx - qr_size / 2, qr_bottom, qr_size)
        c.setFillColor(INK)
        c.setFont("DejaVu-Bold", 17)
        c.drawCentredString(cx, qr_bottom - 7 * mm, _fit(c, label.title, "DejaVu-Bold", 17, cell_w - 8 * mm))
        c.setFillColor(MUTED)
        c.setFont("DejaVu", 8)
        c.drawCentredString(cx, qr_bottom - 11.5 * mm, _fit(c, label.subtitle, "DejaVu", 8, cell_w - 8 * mm))
        c.setFont("DejaVu", 6)
        c.drawCentredString(cx, qr_bottom - 15.5 * mm, L("Fayzi Umar · Учёт пасеки"))
    c.showPage()
    c.save()
    return buf.getvalue()


def _hives(db: Session, data: LabelsRequest) -> list[Hive]:
    stmt = select(Hive)
    if data.hive_ids:
        stmt = stmt.where(Hive.id.in_(data.hive_ids))
    elif data.apiary_id:
        get_apiary(db, data.apiary_id)
        stmt = stmt.where(Hive.apiary_id == data.apiary_id, Hive.status.not_in(ARCHIVED_HIVE_STATUSES))
    else:
        return []
    hives = list(db.scalars(stmt.order_by(natural_order(Hive.hive_number))).unique())
    if data.hive_ids and len(hives) != len(set(data.hive_ids)):
        raise NotFoundError("Некоторые ульи не найдены")
    if len(hives) > MAX_LABEL_HIVES:
        raise ValidationFailed(f"За один раз можно напечатать не больше {MAX_LABEL_HIVES} наклеек")
    return hives


def build(db: Session, data: LabelsRequest) -> tuple[bytes, list[Hive]]:
    """PDF bytes and the hives on it. Nothing is written to the database here."""
    hives = _hives(db, data)
    labels = []
    for hive in hives:
        qr = qr_service.find(db, hive.id)
        code = qr.code if qr else qr_service.payload(hive.id)
        labels.append(Label(qr_service.qr_content(code), L(f"Улей №{hive.hive_number}"), hive.apiary.name))
    for _ in range(data.blank_count):
        new_id = uuid.uuid4()
        labels.append(Label(qr_service.qr_content(qr_service.payload(new_id)), L("Новый улей"), L(f"код …{str(new_id)[-8:]}")))
    if not labels:
        raise ValidationFailed("На выбранной пасеке нет ульев. Укажите количество пустых наклеек.")
    return render(labels), hives


def mark_printed(db: Session, hives: list[Hive], user: User) -> None:
    now = datetime.now(UTC)
    for hive in hives:
        qr = qr_service.ensure(db, hive, user)
        qr.print_count += 1
        qr.last_printed_at = now
        audit.record(db, user=user, entity_type="qr_code", entity_id=qr.id, hive_id=hive.id,
                     action="qr_printed", new={"print_count": qr.print_count})
    db.commit()


def filename() -> str:
    return f"qr-labels-{datetime.now(UTC):%Y%m%d-%H%M}.pdf"
