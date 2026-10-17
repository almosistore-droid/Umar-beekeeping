"""Home screen: counters and chart series in one request (stage 6, user story 1)."""
from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ARCHIVED_HIVE_STATUSES, FamilyStrength, Hive, HiveStatus, Queen
from app.models.enums import DiseaseCaseStatus
from app.models.health import Disease, HiveDisease
from app.schemas.common import today
from app.config import get_settings
from app.schemas.report import Bucket, DashboardFinance, DashboardOut, DashboardTiles, DiseaseCount
from app.services import health_service, honey_service, stock_service
from app.utils.age import age_in_months
from app.utils.labels import STRENGTH

STRENGTH_ORDER = [FamilyStrength.VERY_WEAK, FamilyStrength.WEAK, FamilyStrength.MEDIUM,
                  FamilyStrength.STRONG, FamilyStrength.VERY_STRONG]
AGE_BUCKETS = [("lt1", "до 1 года"), ("1", "1 год"), ("2", "2 года"), ("3plus", "3 года и старше"), ("unknown", "неизвестно")]


def age_bucket(months: int | None) -> str:
    if months is None:
        return "unknown"
    years = months // 12
    return "lt1" if years < 1 else "1" if years == 1 else "2" if years == 2 else "3plus"


def disease_counts(db: Session, year: int) -> list[DiseaseCount]:
    rows = db.execute(
        select(Disease.name, HiveDisease.status, func.count())
        .join(Disease, Disease.id == HiveDisease.disease_id)
        .where(func.extract("year", HiveDisease.detected_at) == year)
        .group_by(Disease.name, HiveDisease.status)
    ).all()
    agg: dict[str, list[int]] = {}
    for name, status, n in rows:
        a = agg.setdefault(name, [0, 0])
        a[0] += n
        if status == DiseaseCaseStatus.RESOLVED:
            a[1] += n
    out = [DiseaseCount(name=k, cases=v[0], resolved=v[1], open=v[0] - v[1]) for k, v in agg.items()]
    return sorted(out, key=lambda d: (-d.cases, d.name))


def finance(db: Session, year: int) -> DashboardFinance:
    from app.services import crm_service as crm
    inc, exp = crm.income(db, year), crm.expenses_total(db, year)
    inc_m, exp_m = crm.by_month(db, year)
    return DashboardFinance(currency=get_settings().currency, income=inc, expenses=exp, profit=inc - exp,
                            debts_total=sum((d.debt for d in crm.debts(db)), crm.ZERO),
                            income_by_month=inc_m, expenses_by_month=exp_m)


def dashboard(db: Session, year: int, show_finance: bool = False) -> DashboardOut:
    hives = list(db.scalars(select(Hive).where(Hive.status.not_in(ARCHIVED_HIVE_STATUSES))).unique())
    strengths = Counter(h.current_family.strength for h in hives if h.current_family)
    att = health_service.attention(db)
    honey = honey_service.stats(db, year)

    t = today()
    queens = list(db.scalars(select(Queen).join(Hive, Hive.current_queen_id == Queen.id)
                             .where(Hive.status.not_in(ARCHIVED_HIVE_STATUSES))).unique())
    ages = Counter(age_bucket(age_in_months(q.birth_date, q.birth_year, t)) for q in queens)

    return DashboardOut(
        year=year,
        tiles=DashboardTiles(
            hives=len(hives), queens_in_hives=len(queens),
            strong=strengths[FamilyStrength.STRONG] + strengths[FamilyStrength.VERY_STRONG],
            weak=strengths[FamilyStrength.WEAK] + strengths[FamilyStrength.VERY_WEAK],
            sick=att["sick"], queenless=sum(1 for h in hives if h.status == HiveStatus.QUEENLESS),
            needs_inspection=att["needs_inspection"], open_tasks=att["open_tasks"], overdue_tasks=att["overdue_tasks"],
            honey_year_kg=honey["year_kg"], best_hive=honey["best_hive"],
        ),
        finance=finance(db, year) if show_finance else None,
        honey_by_month=honey["by_month"],
        honey_by_hive=honey["by_hive"][:10],
        strength=[Bucket(key=s.value, label=STRENGTH[s].capitalize(), count=strengths[s]) for s in STRENGTH_ORDER],
        diseases=disease_counts(db, year),
        stock_low=stock_service.low_items(db),
        queen_ages=[Bucket(key=k, label=label, count=ages[k]) for k, label in AGE_BUCKETS],
    )
