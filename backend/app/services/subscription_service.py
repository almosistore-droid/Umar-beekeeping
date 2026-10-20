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

from app.config import Settings, get_settings
from app.database import SessionLocal
from app.models import InstallationState
from app.services import audit_service as audit

CACHE_SECONDS = 15
_cache: tuple[float, bool, date | None, bool | None] | None = None


def reset_cache() -> None:
    global _cache
    _cache = None


def _row() -> tuple[bool, date | None, bool | None]:
    global _cache
    now = time.monotonic()
    if _cache and now - _cache[0] < CACHE_SECONDS:
        return _cache[1], _cache[2], _cache[3]
    try:
        with SessionLocal() as db:
            row = db.scalar(select(InstallationState))
            value = (row.subscription_override, row.subscription_until, row.admin_in_app) if row else (False, None, None)
    except Exception:  # noqa: BLE001 — the database is down: fall back to the .env, never lock everyone out
        value = (False, None, None)
    _cache = (now, *value)
    return value


def admin_in_app(settings: Settings) -> bool:
    """Users are managed in the app (by the client's admin) unless the owner moved it to the owner panel."""
    value = _row()[2]
    return settings.admin_in_app if value is None else value


def set_admin_in_app(db: Session, value: bool) -> None:
    before = admin_in_app(get_settings())
    db.execute(insert(InstallationState).values(singleton=True, admin_in_app=value, updated_from="owner panel")
               .on_conflict_do_update(index_elements=["singleton"],
                                      set_={"admin_in_app": value, "updated_at": func.now()}))
    row = db.scalar(select(InstallationState))
    audit.record(db, user=None, entity_type="installation", entity_id=row.id, action="admin_place_set",
                 old={"admin_in_app": before}, new={"admin_in_app": value})
    db.commit()
    reset_cache()


def effective_until(settings: Settings) -> date | None:
    override, until, _ = _row()
    return until if override else settings.subscription_until


def source(settings: Settings) -> str:
    override = _row()[0]
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
