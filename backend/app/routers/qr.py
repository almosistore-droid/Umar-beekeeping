import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.dependencies import CAN_WRITE, CurrentUser, require_roles
from app.database import get_db
from app.models import User
from app.schemas.qr import LabelsRequest, LabelsSentOut, QrOut, QrResolveOut, QrStatusOut
from app.services import hive_service, qr_labels, qr_service, telegram_bot
from app.utils.age import plural_ru as plural

router = APIRouter(prefix="/api", tags=["qr"])
DB = Annotated[Session, Depends(get_db)]
Writer = Annotated[User, Depends(require_roles(*CAN_WRITE))]


@router.get("/hives/{hive_id}/qr", response_model=QrOut)
def get_hive_qr(hive_id: uuid.UUID, db: DB, _: CurrentUser):
    hive = hive_service.get_hive(db, hive_id)
    qr = qr_service.find(db, hive.id)
    if qr is None:  # not expected after migration 0005; show the same permanent payload
        from app.models import QrCode
        qr = QrCode(hive_id=hive.id, code=qr_service.payload(hive.id), print_count=0)
    return qr_service.to_out(hive, qr)


@router.post("/hives/{hive_id}/qr", response_model=QrOut)
def ensure_hive_qr(hive_id: uuid.UUID, db: DB, user: Writer):
    """Create the QR if missing. Idempotent: an existing code is never changed."""
    hive = hive_service.get_hive(db, hive_id)
    qr = qr_service.ensure(db, hive, user)
    db.commit()
    return qr_service.to_out(hive, qr)


@router.get("/qr/status", response_model=QrStatusOut)
def qr_status(_: CurrentUser):
    """Whether printed QR codes will contain a Telegram deep link (bot username configured)."""
    link = qr_service.deep_link("hive_…")
    return QrStatusOut(deep_link_ready=link is not None, example_link=link)


@router.get("/qr/resolve", response_model=QrResolveOut)
def resolve_qr(db: DB, user: CurrentUser, code: Annotated[str, Query(max_length=2048)] = ""):
    return qr_service.resolve(db, code, user)


@router.post("/qr/labels", response_model=LabelsSentOut,
             responses={200: {"content": {"application/pdf": {}}, "description": "PDF when delivery=download"}})
def print_labels(body: LabelsRequest, db: DB, user: Writer):
    pdf, hives = qr_labels.build(db, body)
    total = len(hives) + body.blank_count
    name = qr_labels.filename()
    if body.delivery == "telegram":
        caption = f"QR-наклейки: {total} {plural(total, 'наклейка', 'наклейки', 'наклеек')}. Распечатайте на A4 без масштабирования."
        telegram_bot.send_document(user.telegram_id, name, pdf, caption)
        qr_labels.mark_printed(db, hives, user)
        return LabelsSentOut(sent=True, labels=total)
    qr_labels.mark_printed(db, hives, user)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{name}"'})
