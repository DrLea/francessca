"""Schemas for the lawyer portal, client orders, feedback and reviews."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.lawyer_application import _csv


def _clean_list(value: list[str]) -> list[str]:
    return [item.strip()[:64] for item in value if item and item.strip()]


# --- Registration -------------------------------------------------------
class LawyerRegisterRequest(BaseModel):
    """Deliberately short: name, email, password and where they practise.
    Everything else is filled in later from the profile editor."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=2, max_length=255)
    city: str | None = Field(default=None, max_length=128)
    law_firm: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=64)
    specializations: list[str] = Field(default_factory=list, max_length=12)
    languages: list[str] = Field(default_factory=list, max_length=12)
    language: str = Field(default="en", max_length=8)  # UI language

    @field_validator("specializations", "languages")
    @classmethod
    def _clean(cls, value: list[str]) -> list[str]:
        return _clean_list(value)


# --- Profile ------------------------------------------------------------
class LawyerProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    law_firm: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=128)
    email: EmailStr | None = None  # public contact address
    phone: str | None = Field(default=None, max_length=64)
    website: str | None = Field(default=None, max_length=512)
    address: str | None = Field(default=None, max_length=1_000)
    photo_url: str | None = Field(default=None, max_length=512)
    bio: str | None = Field(default=None, max_length=4_000)
    years_experience: int | None = Field(default=None, ge=0, le=80)
    consultation_fee: str | None = Field(default=None, max_length=128)
    office_hours: str | None = Field(default=None, max_length=255)
    specializations: list[str] | None = Field(default=None, max_length=12)
    languages: list[str] | None = Field(default=None, max_length=12)

    @field_validator("specializations", "languages")
    @classmethod
    def _clean(cls, value: list[str] | None) -> list[str] | None:
        return None if value is None else _clean_list(value)

    @field_validator("website", "photo_url")
    @classmethod
    def _http_only(cls, value: str | None) -> str | None:
        # These are rendered as links/images for other users.
        if value and not value.lower().startswith(("http://", "https://")):
            raise ValueError("Must start with http:// or https://")
        return value


class LawyerProfileOut(BaseModel):
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
    bio: str | None
    years_experience: int | None
    consultation_fee: str | None
    office_hours: str | None
    is_published: bool
    rating_avg: float | None
    rating_count: int
    languages: list[str] = Field(default_factory=list)
    specializations: list[str] = Field(default_factory=list)

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


class QuotaOut(BaseModel):
    free_total: int
    extra: int
    used: int
    remaining: int
    free_remaining: int
    contact_email: str | None


class LawyerMeOut(BaseModel):
    # pending | approved | rejected
    approval: str
    profile: LawyerProfileOut
    quota: QuotaOut
    # 0-100, how much of the profile is filled in.
    profile_completeness: int


# --- Orders -------------------------------------------------------------
class OrderCreate(BaseModel):
    lawyer_id: int
    # One of these, or neither (message only). `conversation_id` builds a
    # fresh summary from that conversation first.
    case_id: int | None = None
    conversation_id: int | None = None
    message: str | None = Field(default=None, max_length=2_000)


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rating: int
    comment: str | None
    created_at: datetime


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2_000)


class OrderLawyerRef(BaseModel):
    id: int
    name: str
    law_firm: str | None
    city: str | None
    email: str | None
    phone: str | None


class ClientOrderOut(BaseModel):
    """An order as the client who sent it sees it."""

    id: int
    status: str
    lawyer: OrderLawyerRef
    case_title: str | None
    message: str | None
    quality_score: int
    created_at: datetime
    responded_at: datetime | None
    closed_at: datetime | None
    review: ReviewOut | None
    can_review: bool


class OrderClientRef(BaseModel):
    name: str | None
    email: str
    language: str


class LawyerOrderOut(BaseModel):
    """An order as the lawyer who received it sees it. `client` stays null
    until the lawyer accepts — that is what an order buys."""

    id: int
    status: str
    case_title: str | None
    case_type: str | None
    case_summary: dict
    message: str | None
    quality_score: int
    quality_breakdown: dict
    is_free: bool
    deal_value: float | None
    created_at: datetime
    responded_at: datetime | None
    closed_at: datetime | None
    client: OrderClientRef | None
    review: ReviewOut | None


class OrderClose(BaseModel):
    outcome: Literal["won", "lost"]
    # The lawyer's own figure for the finance section; optional.
    deal_value: float | None = Field(default=None, ge=0, le=100_000_000)


# --- Feedback -----------------------------------------------------------
class FeedbackCreate(BaseModel):
    category: Literal["lead_quality", "platform", "bug", "idea", "other"] = "lead_quality"
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str = Field(min_length=3, max_length=4_000)
    order_id: int | None = None


class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lawyer_id: int
    order_id: int | None
    category: str
    rating: int | None
    comment: str
    status: str
    admin_note: str | None
    created_at: datetime


class AdminFeedbackOut(FeedbackOut):
    lawyer_name: str
    lawyer_city: str | None
    # The lead the comment is about, to set the lawyer's opinion against
    # the automatic score.
    order_quality_score: int | None
    order_case_title: str | None


class AdminFeedbackUpdate(BaseModel):
    status: Literal["new", "reviewed"] | None = None
    admin_note: str | None = Field(default=None, max_length=4_000)


class AdminLawyerUpdate(BaseModel):
    is_published: bool | None = None
    extra_orders: int | None = Field(default=None, ge=0, le=100_000)
