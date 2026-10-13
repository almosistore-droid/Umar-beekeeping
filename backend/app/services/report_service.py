"""Yearly report (stage 6, user story 2). Read-only: everything is derived from stored history.

A hive exists from its installation date (or creation) until its archive date, which is taken
from history: the merge date for merged hives, the audit entry that set SOLD/LOST otherwise.
"""
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ARCHIVED_HIVE_STATUSES, Hive, HiveStatus, Queen, QueenStatus
from app.models.audit import AuditLog
from app.models.health import HiveDisease, Treatment
from app.models.hive import QueenAssignment
from app.models.operations import HiveMerge, HiveSplit, HoneyHarvest, OtherProduct, hive_merge_sources
from app.schemas.common import today
from app.schemas.report import (
    BestFamily,
    DiseasesSection,
    FinanceSection,
    HivesSection,
    HoneySection,
    MedicationCount,
    MoneyByKey,
    ProductTotal,
    QueensSection,
    YearlyReportOut,
)
from app.services import honey_service
from app.services.dashboard_service import disease_counts
from app.utils.age import age_in_months
from app.utils.errors import ValidationFailed

ZERO = Decimal("0")
FIRST_YEAR = 2000


@dataclass
class Span:
    hive: Hive
    start: date
    end: date | None  # archive date
    status: HiveStatus


def validate_year(year: int) -> None:
    current = today().year
    if not FIRST_YEAR <= year <= current:
        raise ValidationFailed(f"Год отчёта должен быть от {FIRST_YEAR} до {current}")


def _period(year: int) -> tuple[date, date]:
    return date(year, 1, 1), min(date(year, 12, 31), today())


def hive_spans(db: Session) -> list[Span]:
    merged = dict(db.execute(
        select(hive_merge_sources.c.hive_id, func.min(HiveMerge.merge_date))
        .join(HiveMerge, HiveMerge.id == hive_merge_sources.c.merge_id)
        .group_by(hive_merge_sources.c.hive_id)
    ).all())
    left = dict(db.execute(
        select(AuditLog.entity_id, func.min(AuditLog.created_at))
        .where(AuditLog.entity_type == "hive", AuditLog.new_value["status"].astext.in_(["SOLD", "LOST"]))
        .group_by(AuditLog.entity_id)
    ).all())
    spans = []
    for h in db.scalars(select(Hive)).unique():
        end = None
        if h.status in ARCHIVED_HIVE_STATUSES:
            if h.status == HiveStatus.MERGED and h.id in merged:
                end = merged[h.id]
            elif h.id in left:
                end = left[h.id].date()
            else:
                end = h.updated_at.date()
        spans.append(Span(h, h.installation_date or h.created_at.date(), end, h.status))
    return spans


def _hives(db: Session, spans: list[Span], y0: date, y1: date) -> HivesSection:
    def archived(status: HiveStatus) -> int:
        return sum(1 for s in spans if s.status == status and s.end and y0 <= s.end <= y1)

    return HivesSection(
        at_start=sum(1 for s in spans if s.start < y0 and (s.end is None or s.end >= y0)),
        at_end=sum(1 for s in spans if s.start <= y1 and (s.end is None or s.end > y1)),
        new=sum(1 for s in spans if y0 <= s.start <= y1),
        lost=archived(HiveStatus.LOST), sold=archived(HiveStatus.SOLD), merged=archived(HiveStatus.MERGED),
        split=db.scalar(select(func.count()).select_from(HiveSplit)
                        .where(HiveSplit.split_date.between(y0, y1))) or 0,
    )


def _queens(db: Session, y0: date, y1: date, by_hive) -> QueensSection:
    active_end = list(db.scalars(select(QueenAssignment).where(
        QueenAssignment.installed_at <= y1,
        (QueenAssignment.removed_at.is_(None)) | (QueenAssignment.removed_at > y1))).unique())
    queen_by_hive: dict[uuid.UUID, str] = {a.hive_id: a.queen.queen_code for a in active_end}
    queens = {a.queen_id: a.queen for a in active_end}
    ages = [age_in_months(q.birth_date, q.birth_year, y1) for q in queens.values()]
    known = [a for a in ages if a is not None]

    first_installed = select(QueenAssignment.queen_id, func.min(QueenAssignment.installed_at).label("first")) \
        .group_by(QueenAssignment.queen_id).subquery()
    new = db.scalar(select(func.count()).select_from(first_installed)
                    .where(first_installed.c.first.between(y0, y1))) or 0
    replaced = db.scalar(select(func.count(func.distinct(QueenAssignment.queen_id)))
                         .join(Queen, Queen.id == QueenAssignment.queen_id)
                         .where(Queen.status == QueenStatus.REPLACED,
                                QueenAssignment.removed_at.between(y0, y1))) or 0
    return QueensSection(
        in_hives=len(queens), new=new, replaced=replaced,
        avg_age_months=(Decimal(sum(known)) / len(known)).quantize(Decimal("0.1")) if known else None,
        age_unknown=len(ages) - len(known),
        best_families=[BestFamily(hive_id=r.hive_id, hive_number=r.hive_number, apiary_name=r.apiary_name, kg=r.kg,
                                  queen_code=queen_by_hive.get(r.hive_id)) for r in by_hive[:5]],
    )


def _honey(db: Session, year: int, y0: date, y1: date, stats: dict) -> HoneySection:
    products = [
        ProductTotal(product_type=t, unit=u, quantity=q, value=v or ZERO)
        for t, u, q, v in db.execute(
            select(OtherProduct.product_type, OtherProduct.unit, func.sum(OtherProduct.quantity),
                   func.sum(OtherProduct.total_value))
            .where(OtherProduct.collected_at.between(y0, y1))
            .group_by(OtherProduct.product_type, OtherProduct.unit)
            .order_by(OtherProduct.product_type)
        ).all()
    ]
    by_hive = stats["by_hive"]
    return HoneySection(
        total_kg=stats["year_kg"], avg_per_hive_kg=stats["avg_per_hive_kg"], producing_hives=stats["producing_hives"],
        best_hive=by_hive[0] if by_hive else None, worst_hive=by_hive[-1] if len(by_hive) > 1 else None,
        by_month=stats["by_month"], by_hive=by_hive, value=stats["year_value"], products=products,
    )


def _diseases(db: Session, year: int, y0: date, y1: date) -> DiseasesSection:
    by_disease = disease_counts(db, year)
    meds = db.execute(
        select(Treatment.medication, func.count()).where(Treatment.treated_at.between(y0, y1))
        .group_by(Treatment.medication).order_by(func.count().desc(), Treatment.medication)
    ).all()
    return DiseasesSection(
        cases=sum(d.cases for d in by_disease), resolved=sum(d.resolved for d in by_disease),
        open=sum(d.open for d in by_disease), by_disease=by_disease,
        treatments=sum(n for _, n in meds), medications=[MedicationCount(medication=m, count=n) for m, n in meds[:5]],
    )


def available_years(db: Session, spans: list[Span]) -> list[int]:
    current = today().year
    first = min([s.start.year for s in spans] + [db.scalar(select(func.min(HoneyHarvest.harvest_year))) or current,
                                                  current])
    first = max(first, FIRST_YEAR)
    return list(range(current, first - 1, -1))


def _finance(db: Session, year: int, production_value: Decimal, show: bool) -> FinanceSection:
    from app.config import get_settings
    from app.services import crm_service as crm
    currency = get_settings().currency
    if not show:
        return FinanceSection(production_value=production_value, visible=False, currency=currency)
    inc, exp = crm.income(db, year), crm.expenses_total(db, year)
    return FinanceSection(
        production_value=production_value, visible=True, currency=currency, income=inc, expenses=exp, profit=inc - exp,
        received=crm.received(db, year), debts_total=sum((d.debt for d in crm.debts(db)), ZERO),
        income_by_category=[MoneyByKey(**x.model_dump()) for x in crm.income_by_category(db, year)],
        expenses_by_category=[MoneyByKey(**x.model_dump()) for x in crm.expenses_by_category(db, year)],
    )


def yearly(db: Session, year: int, show_finance: bool = False) -> YearlyReportOut:
    validate_year(year)
    y0, y1 = _period(year)
    spans = hive_spans(db)
    stats = honey_service.stats(db, year)
    honey = _honey(db, year, y0, y1, stats)
    return YearlyReportOut(
        year=year, period_end=y1.isoformat(), is_partial=y1 < date(year, 12, 31),
        hives=_hives(db, spans, y0, y1),
        queens=_queens(db, y0, y1, stats["by_hive"]),
        honey=honey,
        diseases=_diseases(db, year, y0, y1),
        finance=_finance(db, year, honey.value + sum((p.value for p in honey.products), ZERO), show_finance),
        available_years=available_years(db, spans),
    )
