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
