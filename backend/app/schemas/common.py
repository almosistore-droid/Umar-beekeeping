from datetime import date, datetime, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict

from app.config import get_settings


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


@lru_cache
def _zone(name: str) -> ZoneInfo:
    return ZoneInfo(name)


def app_zone() -> ZoneInfo:
    return _zone(get_settings().timezone)


def today() -> date:
    """Today's date at the apiary (settings.timezone), not in UTC: at 00:30 in Dushanbe it is already tomorrow."""
    return datetime.now(app_zone()).date()


def local_date(moment: datetime) -> date:
    """Calendar day of a stored timestamp at the apiary."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(app_zone()).date()


def not_in_future(value: date | None, label: str) -> date | None:
    # One day of slack: the beekeeper's local date may be ahead of UTC
    if value is not None and (value - today()).days > 1:
        raise ValueError(f"{label} не может быть в будущем")
    return value


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def stored_day(moment: datetime) -> date:
    """A calendar date stored as noon UTC (next inspection): read it back in UTC, whatever the zone."""
    if moment.tzinfo is None:
        return moment.date()
    return moment.astimezone(timezone.utc).date()

