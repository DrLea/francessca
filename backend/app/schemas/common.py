"""Shared schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class MessageResponse(BaseModel):
    detail: str


class UsageOut(BaseModel):
    token_limit: int | None
    tokens_used: int
    tokens_remaining: int | None
    tier: str


class DashboardOut(BaseModel):
    conversations: int
    documents: int
    cases: int
    exports: int
    tokens_used: int
    token_limit: int | None


class DocumentOut(BaseModel):
    id: int
    filename: str
    size: int
    mime: str
    uploaded_at: datetime
    has_extracted_text: bool

    class Config:
        from_attributes = True
