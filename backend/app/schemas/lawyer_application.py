"""Lawyer sign-up application schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.lawyer_application import ApplicationStatus


def _csv(value: object) -> list[str]:
    """Stored comma-separated, exposed as a list."""
    if isinstance(value, str):
        return [s.strip() for s in value.split(",") if s.strip()]
    return list(value or [])


class LawyerApplicationCreate(BaseModel):
    """What a lawyer submits from the landing page. Public, unauthenticated —
    so everything is length-capped and nothing here is ever published until
    an admin approves it."""

    name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    law_firm: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=128)
    phone: str | None = Field(default=None, max_length=64)
    website: str | None = Field(default=None, max_length=512)
    address: str | None = Field(default=None, max_length=1_000)
    specializations: list[str] = Field(default_factory=list, max_length=12)
    languages: list[str] = Field(default_factory=list, max_length=12)
    message: str | None = Field(default=None, max_length=2_000)

    @field_validator("specializations", "languages")
    @classmethod
    def _clean_list(cls, value: list[str]) -> list[str]:
        return [item.strip()[:64] for item in value if item and item.strip()]


class LawyerApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    law_firm: str | None
    city: str | None
    phone: str | None
    website: str | None
    address: str | None
    message: str | None
    status: ApplicationStatus
    lawyer_id: int | None
    # Set when the lawyer registered an account (the lawyer portal).
    user_id: int | None = None
    reviewed_at: datetime | None
    created_at: datetime
    specializations: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)

    @field_validator("specializations", "languages", mode="before")
    @classmethod
    def _split(cls, value: object) -> list[str]:
        return _csv(value)


class LawyerPublicOut(BaseModel):
    """The directory as shown to visitors who are not signed in: enough to
    see who is on the list, without handing out contact details."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    law_firm: str | None
    city: str | None
    specializations: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)

    @field_validator("languages", mode="before")
    @classmethod
    def _split_langs(cls, value: object) -> list[str]:
        return _csv(value)

    @field_validator("specializations", mode="before")
    @classmethod
    def _spec_names(cls, value: object) -> list[str]:
        return [
            item.name if hasattr(item, "name") else str(item) for item in value or []
        ]
