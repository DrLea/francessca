"""Lawyer schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LawyerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    law_firm: str | None
    city: str | None
    email: str | None
    phone: str | None
    website: str | None
    address: str | None
    photo_url: str | None
    profile_url: str | None
    languages: list[str] = Field(default_factory=list)
    specializations: list[str] = Field(default_factory=list)
    last_synced_at: datetime | None = None

    @field_validator("languages", mode="before")
    @classmethod
    def _split_langs(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v or []

    @field_validator("specializations", mode="before")
    @classmethod
    def _spec_names(cls, v: object) -> list[str]:
        out: list[str] = []
        for item in v or []:
            out.append(item.name if hasattr(item, "name") else str(item))
        return out


class LawyerSearchResult(BaseModel):
    total: int
    items: list[LawyerOut]
