"""User schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import UserRole, UserTier


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None
    language: str
    role: UserRole
    tier: UserTier
    token_limit: int | None
    tokens_used: int
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: str | None = None
    language: str | None = None


class AdminUserUpdate(BaseModel):
    """Fields an admin may modify."""

    tier: UserTier | None = None
    token_limit: int | None = None
    tokens_used: int | None = None
    role: UserRole | None = None
