"""Auth-related request/response schemas."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
    language: str = Field(default="en", max_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    # The Google ID token obtained client-side.
    id_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
