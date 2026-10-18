"""Paid-until date of this installation.

Effective date = the database row (set from the owner panel or `python -m app.utils.subscription`) when it exists,
otherwise SUBSCRIPTION_UNTIL from the .env. The row is cached for a few seconds: the subscription check runs on
every request.
"""
import time
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import SessionLocal
from app.models import InstallationState
from app.services import audit_service as audit

CACHE_SECONDS = 15
_cache: tuple[float, bool, date | None] | None = None


def reset_cache() -> None:
    global _cache
    _cache = None


def _row() -> tuple[bool, date | None]:
    global _cache
    now = time.monotonic()
    if _cache and now - _cache[0] < CACHE_SECONDS:
        return _cache[1], _cache[2]
    try:
        with SessionLocal() as db:
            row = db.scalar(select(InstallationState))
            value = (row.subscription_override, row.subscription_until) if row else (False, None)
    except Exception:  # noqa: BLE001 — the database is down: fall back to the .env, never lock everyone out
        value = (False, None)
    _cache = (now, *value)
    return value


def effective_until(settings: Settings) -> date | None:
    override, until = _row()
    return until if override else settings.subscription_until


def source(settings: Settings) -> str:
    override, _ = _row()
    return "panel" if override else ("env" if settings.subscription_until else "none")


def set_until(db: Session, until: date | None, updated_from: str) -> InstallationState:
    """`until=None` means no limit. Recorded in the activity log."""
    before = db.scalar(select(InstallationState))
    old = before.subscription_until.isoformat() if before and before.subscription_until else None
    db.execute(insert(InstallationState).values(singleton=True, subscription_override=True, subscription_until=until,
                                                updated_from=updated_from)
               .on_conflict_do_update(index_elements=["singleton"],
                                      set_={"subscription_override": True, "subscription_until": until,
                                            "updated_from": updated_from, "updated_at": func.now()}))
    row = db.scalar(select(InstallationState))
    audit.record(db, user=None, entity_type="installation", entity_id=row.id, action="subscription_set",
                 old={"until": old}, new={"until": until.isoformat() if until else None, "from": updated_from})
    db.commit()
    reset_cache()
    return row
