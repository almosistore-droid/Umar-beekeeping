import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel, clean_text


class ApiaryBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=5000)
    address: str | None = Field(default=None, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Название пасеки не может быть пустым")
        return v

    @field_validator("description", "address")
    @classmethod
    def _clean(cls, v):
        return clean_text(v)


class ApiaryCreate(ApiaryBase):
    pass


class ApiaryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=5000)
    address: str | None = Field(default=None, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    is_archived: bool | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, v):
        if v is not None and not v.strip():
            raise ValueError("Название пасеки не может быть пустым")
        return v.strip() if v else v


class ApiaryOut(ORMModel):
    id: uuid.UUID
    name: str
    description: str | None
    address: str | None
    latitude: float | None
    longitude: float | None
    owner_id: uuid.UUID | None
    is_archived: bool
    hive_count: int = 0
    created_at: datetime
    updated_at: datetime


class ApiaryBrief(ORMModel):
    id: uuid.UUID
    name: str
