"""Chat schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.message import MessageRole


class ChatRequest(BaseModel):
    conversation_id: int | None = None
    message: str = Field(min_length=1, max_length=20_000)
    # Optional document ids whose extracted text should be added to context.
    document_ids: list[int] = Field(default_factory=list)


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: MessageRole
    content: str
    token_count: int
    created_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = Field(default_factory=list)


class ChatResponse(BaseModel):
    conversation_id: int
    message: MessageOut
    tokens_used: int
    tokens_remaining: int | None
