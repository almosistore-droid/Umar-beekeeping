import uuid
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import FeedUnit, ProductType
from app.schemas.operations import HiveRank


class Bucket(BaseModel):
    key: str
    label: str
    count: int


class DiseaseCount(BaseModel):
    name: str
    cases: int
    resolved: int
    open: int


class DashboardTiles(BaseModel):
    hives: int
    queens_in_hives: int
    strong: int
    weak: int
    sick: int
    queenless: int
    needs_inspection: int
    open_tasks: int
    overdue_tasks: int
    honey_year_kg: Decimal
    best_hive: HiveRank | None


class DashboardFinance(BaseModel):
    currency: str
    income: Decimal
    expenses: Decimal
    profit: Decimal
    debts_total: Decimal
    income_by_month: list[Decimal]
    expenses_by_month: list[Decimal]


class DashboardOut(BaseModel):
    year: int
    tiles: DashboardTiles
    finance: DashboardFinance | None  # only for ADMIN / BEEKEEPER
    honey_by_month: list[Decimal]
    honey_by_hive: list[HiveRank]
    strength: list[Bucket]
    diseases: list[DiseaseCount]
    queen_ages: list[Bucket]


# ---------- yearly report ----------

class HivesSection(BaseModel):
    at_start: int
    at_end: int
    new: int
    lost: int
    sold: int
    merged: int
    split: int


class BestFamily(BaseModel):
    hive_id: uuid.UUID
    hive_number: str
    apiary_name: str
    kg: Decimal
    queen_code: str | None


class QueensSection(BaseModel):
    in_hives: int
    new: int
    replaced: int
    avg_age_months: Decimal | None
    age_unknown: int
    best_families: list[BestFamily]


class ProductTotal(BaseModel):
    product_type: ProductType
    unit: FeedUnit
    quantity: Decimal
    value: Decimal


class HoneySection(BaseModel):
    total_kg: Decimal
    avg_per_hive_kg: Decimal
    producing_hives: int
    best_hive: HiveRank | None
    worst_hive: HiveRank | None
    by_month: list[Decimal]
    by_hive: list[HiveRank]
    value: Decimal
    products: list[ProductTotal]


class MedicationCount(BaseModel):
    medication: str
    count: int


class DiseasesSection(BaseModel):
    cases: int
    resolved: int
    open: int
    by_disease: list[DiseaseCount]
    treatments: int
    medications: list[MedicationCount]


class MoneyByKey(BaseModel):
    key: str
    label: str
    amount: Decimal


class FinanceSection(BaseModel):
    production_value: Decimal  # harvest and products at the prices written in the records
    visible: bool  # money is shown to ADMIN / BEEKEEPER only
    currency: str
    income: Decimal | None = None
    expenses: Decimal | None = None
    profit: Decimal | None = None
    received: Decimal | None = None
    debts_total: Decimal | None = None
    income_by_category: list[MoneyByKey] = []
    expenses_by_category: list[MoneyByKey] = []


class YearlyReportOut(BaseModel):
    year: int
    period_end: str
    is_partial: bool
    hives: HivesSection
    queens: QueensSection
    honey: HoneySection
    diseases: DiseasesSection
    finance: FinanceSection
    available_years: list[int]
