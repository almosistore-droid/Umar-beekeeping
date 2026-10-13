"""Import every model here so Alembic autogenerate sees the full metadata."""
from app.models.apiary import Apiary
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.enums import (
    ARCHIVED_HIVE_STATUSES,
    REMOVED_QUEEN_STATUSES,
    FamilyOrigin,
    FamilyStatus,
    FamilyStrength,
    HiveStatus,
    HiveType,
    QueenOrigin,
    QueenStatus,
)
from app.models.health import Disease, Feeding, HiveDisease, Inspection, Task, Treatment
from app.models.hive import BeeFamily, Hive, Queen, QueenAssignment
from app.models.operations import (
    HiveMerge,
    HiveMovement,
    HiveSplit,
    HoneyHarvest,
    OtherProduct,
    Swarm,
    Wintering,
    hive_merge_sources,
)
from app.models.qr import QrCode
from app.models.user import User, UserRole

__all__ = [
    "QrCode",
    "HiveMerge",
    "HiveMovement",
    "HiveSplit",
    "HoneyHarvest",
    "OtherProduct",
    "Swarm",
    "Wintering",
    "hive_merge_sources",
    "Disease",
    "Feeding",
    "HiveDisease",
    "Inspection",
    "Task",
    "Treatment",
    "ARCHIVED_HIVE_STATUSES",
    "REMOVED_QUEEN_STATUSES",
    "Apiary",
    "AuditLog",
    "Base",
    "BeeFamily",
    "FamilyOrigin",
    "FamilyStatus",
    "FamilyStrength",
    "Hive",
    "HiveStatus",
    "HiveType",
    "Queen",
    "QueenAssignment",
    "QueenOrigin",
    "QueenStatus",
    "User",
    "UserRole",
]
