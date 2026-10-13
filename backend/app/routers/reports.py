from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.dependencies import CAN_MANAGE, CurrentUser
from app.database import get_db
from app.schemas.common import today
from app.schemas.qr import LabelsSentOut
from app.schemas.report import DashboardOut, YearlyReportOut
from app.services import dashboard_service, report_export, report_service, telegram_bot

router = APIRouter(prefix="/api", tags=["reports"])
DB = Annotated[Session, Depends(get_db)]
Format = Literal["pdf", "xlsx", "csv"]
_FORMAT_NAMES = {"pdf": "PDF", "xlsx": "Excel", "csv": "CSV"}


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: DB, user: CurrentUser, year: Annotated[int | None, Query(ge=2000, le=2100)] = None):
    year = year or today().year
    report_service.validate_year(year)
    return dashboard_service.dashboard(db, year, show_finance=user.role in CAN_MANAGE)


@router.get("/reports/yearly/{year}", response_model=YearlyReportOut)
def yearly_report(year: int, db: DB, user: CurrentUser):
    return report_service.yearly(db, year, show_finance=user.role in CAN_MANAGE)


@router.get("/reports/yearly/{year}/export",
            responses={200: {"content": {m: {} for m, _ in report_export.FORMATS.values()}}})
def export_yearly(year: int, db: DB, user: CurrentUser, format: Format = "pdf"):
    content, media, name = report_export.render(report_service.yearly(db, year, show_finance=user.role in CAN_MANAGE), format)
    return Response(content, media_type=media, headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.post("/reports/yearly/{year}/send", response_model=LabelsSentOut)
def send_yearly(year: int, db: DB, user: CurrentUser, format: Format = "pdf"):
    """Inside Telegram on a phone files cannot be downloaded: the bot sends it to the user's own chat."""
    content, media, name = report_export.render(report_service.yearly(db, year, show_finance=user.role in CAN_MANAGE), format)
    telegram_bot.send_document(user.telegram_id, name, content,
                               f"Годовой отчёт за {year} ({_FORMAT_NAMES[format]})", media_type=media)
    return LabelsSentOut(sent=True, labels=1)
