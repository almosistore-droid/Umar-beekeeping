"""Domain enumerations shared by models and schemas."""
import enum


class HiveStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    WEAK = "WEAK"
    STRONG = "STRONG"
    SICK = "SICK"
    QUEENLESS = "QUEENLESS"
    EMPTY = "EMPTY"
    QUARANTINE = "QUARANTINE"
    MERGED = "MERGED"
    SPLIT = "SPLIT"
    SOLD = "SOLD"
    LOST = "LOST"


# A hive in one of these statuses is history: it keeps its records but no longer
# occupies its number in the apiary and cannot receive a new family or queen.
ARCHIVED_HIVE_STATUSES = frozenset({HiveStatus.MERGED, HiveStatus.SOLD, HiveStatus.LOST})


class HiveType(str, enum.Enum):
    DADANT = "DADANT"
    LANGSTROTH = "LANGSTROTH"
    RUTA = "RUTA"
    ALPINE = "ALPINE"
    HORIZONTAL = "HORIZONTAL"  # лежак
    MULTI_BODY = "MULTI_BODY"
    NUCLEUS = "NUCLEUS"  # нуклеус
    OTHER = "OTHER"


class FamilyStrength(str, enum.Enum):
    VERY_WEAK = "VERY_WEAK"
    WEAK = "WEAK"
    MEDIUM = "MEDIUM"
    STRONG = "STRONG"
    VERY_STRONG = "VERY_STRONG"


class FamilyStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    REPLACED = "REPLACED"
    MERGED = "MERGED"
    SOLD = "SOLD"
    DEAD = "DEAD"
    ABSCONDED = "ABSCONDED"  # слёт


class FamilyOrigin(str, enum.Enum):
    PURCHASED = "PURCHASED"
    PACKAGE = "PACKAGE"  # пчелопакет
    NUCLEUS = "NUCLEUS"
    SWARM = "SWARM"
    SPLIT = "SPLIT"
    MERGE = "MERGE"
    OWN = "OWN"
    OTHER = "OTHER"


class QueenStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    GOOD = "GOOD"
    OBSERVATION = "OBSERVATION"
    WEAK = "WEAK"
    LOST = "LOST"
    REPLACED = "REPLACED"
    DEAD = "DEAD"
    SOLD = "SOLD"


# Queens in these statuses are out of service and cannot sit in a hive
REMOVED_QUEEN_STATUSES = frozenset(
    {QueenStatus.LOST, QueenStatus.REPLACED, QueenStatus.DEAD, QueenStatus.SOLD}
)


class QueenOrigin(str, enum.Enum):
    OWN_BRED = "OWN_BRED"
    PURCHASED = "PURCHASED"
    SWARM = "SWARM"
    SUPERSEDURE = "SUPERSEDURE"  # тихая смена
    EMERGENCY = "EMERGENCY"  # свищевая
    UNKNOWN = "UNKNOWN"


# ---------- stage 3: health records ----------

class QueenCondition(str, enum.Enum):
    GOOD = "GOOD"
    NORMAL = "NORMAL"
    POOR = "POOR"
    NOT_SEEN = "NOT_SEEN"


class FoodLevel(str, enum.Enum):
    CRITICAL = "CRITICAL"
    LOW = "LOW"
    NORMAL = "NORMAL"
    ABUNDANT = "ABUNDANT"


class InspectionHealth(str, enum.Enum):
    HEALTHY = "HEALTHY"
    SUSPICIOUS = "SUSPICIOUS"
    SICK = "SICK"


class DiseaseSeverity(str, enum.Enum):
    LIGHT = "LIGHT"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"


class DiseaseCaseStatus(str, enum.Enum):
    SUSPECTED = "SUSPECTED"
    CONFIRMED = "CONFIRMED"
    TREATING = "TREATING"
    RESOLVED = "RESOLVED"


# Order used to forbid going backwards (RESOLVED is final)
CASE_STATUS_ORDER = {
    DiseaseCaseStatus.SUSPECTED: 0,
    DiseaseCaseStatus.CONFIRMED: 1,
    DiseaseCaseStatus.TREATING: 2,
    DiseaseCaseStatus.RESOLVED: 3,
}
ACTIVE_CASE_STATUSES = frozenset({DiseaseCaseStatus.CONFIRMED, DiseaseCaseStatus.TREATING})


class FeedType(str, enum.Enum):
    SUGAR_SYRUP = "SUGAR_SYRUP"
    CANDY = "CANDY"
    HONEY = "HONEY"
    PROTEIN = "PROTEIN"
    POLLEN_SUBSTITUTE = "POLLEN_SUBSTITUTE"
    MEDICATED = "MEDICATED"
    OTHER = "OTHER"


class FeedUnit(str, enum.Enum):
    KG = "KG"
    G = "G"
    L = "L"
    ML = "ML"
    PCS = "PCS"


class TaskKind(str, enum.Enum):
    INSPECTION = "INSPECTION"
    TREATMENT = "TREATMENT"
    FEEDING = "FEEDING"
    OTHER = "OTHER"


class TaskStatus(str, enum.Enum):
    OPEN = "OPEN"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


# ---------- stage 4: harvest & colony operations ----------

class ProductType(str, enum.Enum):
    WAX = "WAX"
    PROPOLIS = "PROPOLIS"
    BEE_BREAD = "BEE_BREAD"
    POLLEN = "POLLEN"
    ROYAL_JELLY = "ROYAL_JELLY"
    QUEENS = "QUEENS"
    COLONIES = "COLONIES"
    PACKAGES = "PACKAGES"


class WinteringResult(str, enum.Enum):
    STRONG = "STRONG"   # перезимовала сильной
    WEAK = "WEAK"       # перезимовала, ослабла
    DIED = "DIED"       # погибла


# ---------- stage 7: CRM ----------

class ExpenseCategory(str, enum.Enum):
    HIVES = "HIVES"            # ульи
    FRAMES = "FRAMES"          # рамки
    FOUNDATION = "FOUNDATION"  # вощина
    FEED = "FEED"              # корм
    MEDICINE = "MEDICINE"      # лекарства
    EQUIPMENT = "EQUIPMENT"    # оборудование
    TRANSPORT = "TRANSPORT"    # транспорт
    FUEL = "FUEL"              # топливо
    QUEENS = "QUEENS"          # матки
    COLONIES = "COLONIES"      # семьи
    REPAIR = "REPAIR"          # ремонт
    OTHER = "OTHER"            # другое


class SaleCategory(str, enum.Enum):
    HONEY = "HONEY"
    WAX = "WAX"
    PROPOLIS = "PROPOLIS"
    BEE_BREAD = "BEE_BREAD"
    POLLEN = "POLLEN"
    QUEENS = "QUEENS"
    COLONIES = "COLONIES"
    PACKAGES = "PACKAGES"
    OTHER = "OTHER"


class PaymentMethod(str, enum.Enum):
    CASH = "CASH"
    CARD = "CARD"
    TRANSFER = "TRANSFER"


class OrderStatus(str, enum.Enum):
    NEW = "NEW"
    READY = "READY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


ORDER_STATUS_ORDER = {OrderStatus.NEW: 0, OrderStatus.READY: 1, OrderStatus.DELIVERED: 2}
