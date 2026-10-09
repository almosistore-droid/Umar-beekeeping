from datetime import date, datetime, timezone

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def today() -> date:
    return datetime.now(timezone.utc).date()


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
