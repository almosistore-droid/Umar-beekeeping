"""Audit log: every important change records who, when, before and after."""
import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.user import User

# Technical columns that are not meaningful in a change history
_SKIP = {"created_at", "updated_at", "version"}


def _json(value: Any) -> Any:
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, (uuid.UUID, Decimal)):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def snapshot(obj: Any, fields: list[str] | None = None) -> dict[str, Any]:
    """JSON-safe dict of an ORM object's column values."""
    mapper = inspect(obj).mapper
    names = fields or [c.key for c in mapper.column_attrs if c.key not in _SKIP]
    return {name: _json(getattr(obj, name)) for name in names}


def diff(before: dict[str, Any], after: dict[str, Any]) -> tuple[dict, dict]:
    """Keep only fields whose value changed."""
    changed = [k for k in after if before.get(k) != after.get(k)]
    return {k: before.get(k) for k in changed}, {k: after[k] for k in changed}


def record(
    db: Session,
    *,
    user: User | None,
    entity_type: str,
    entity_id: uuid.UUID,
    action: str,
    old: dict | None = None,
    new: dict | None = None,
    hive_id: uuid.UUID | None = None,
    comment: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user.id if user else None,
        entity_type=entity_type,
        entity_id=entity_id,
        hive_id=hive_id,
        action=action,
        old_value=old or None,
        new_value=new or None,
        comment=comment,
    )
    db.add(entry)
    return entry
