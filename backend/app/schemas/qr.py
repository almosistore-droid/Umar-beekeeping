import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class QrOut(BaseModel):
    hive_id: uuid.UUID
    hive_number: str
    apiary_name: str
    code: str
    deep_link: str | None
    # What the QR image actually encodes: the deep link when configured, otherwise the bare code
    content: str
    deep_link_ready: bool
    svg_data_uri: str
    print_count: int
    last_printed_at: datetime | None


class QrStatusOut(BaseModel):
    deep_link_ready: bool
    example_link: str | None


class QrResolveOut(BaseModel):
    status: Literal["found", "unknown", "invalid"]
    hive_id: uuid.UUID | None = None
    hive_number: str | None = None
    apiary_name: str | None = None
    is_archived: bool = False
    can_register: bool = False


MAX_LABEL_HIVES = 300
MAX_BLANK_LABELS = 60


class LabelsRequest(BaseModel):
    hive_ids: list[uuid.UUID] = Field(default_factory=list, max_length=MAX_LABEL_HIVES)
    apiary_id: uuid.UUID | None = None
    blank_count: int = Field(default=0, ge=0, le=MAX_BLANK_LABELS)
    delivery: Literal["download", "telegram"] = "download"

    @model_validator(mode="after")
    def _something(self):
        if not self.hive_ids and not self.apiary_id and not self.blank_count:
            raise ValueError("Выберите ульи, пасеку или укажите количество пустых наклеек")
        return self


class LabelsSentOut(BaseModel):
    sent: bool
    labels: int
