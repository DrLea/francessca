"""Chat schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.message import MessageRole


class ClarifyQuestion(BaseModel):
    """One clarifying question the assistant attached to its reply.

    `choices` may be empty, in which case the client shows a free-text field.
    The client ALWAYS appends its own "Other" option with a free-text field,
    so the model must not include one.
    """

    question: str
    choices: list[str] = Field(default_factory=list)


class ClarifyAnswer(BaseModel):
    """One answer coming back. `answer` is None/empty when it was skipped."""

    question: str = Field(max_length=300)
    answer: str | None = Field(default=None, max_length=2_000)


class ChatRequest(BaseModel):
    conversation_id: int | None = None
    # Either a free-typed message, or answers to the questions from the
    # previous assistant turn, or both. Answers are folded into a single user
    # message server-side, so a batch of answers still costs exactly one
    # model call -- the same as any other turn.
    message: str = Field(default="", max_length=20_000)
    answers: list[ClarifyAnswer] = Field(default_factory=list, max_length=10)
    # Optional document ids whose extracted text should be added to context.
    document_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def _needs_content(self) -> "ChatRequest":
        if not self.message.strip() and not self.answers:
            raise ValueError("message or answers is required")
        return self


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: MessageRole
    content: str
    token_count: int
    created_at: datetime
    # Present only on assistant turns that ended with a question block.
    questions: list[ClarifyQuestion] = Field(default_factory=list)

    @field_validator("questions", mode="before")
    @classmethod
    def _null_is_empty(cls, value: object) -> object:
        # The column is NULL for every ordinary message.
        return value or []


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = Field(default_factory=list)


class ChatResponse(BaseModel):
    conversation_id: int
    # The stored user turn, so the client can render exactly what was saved
    # (answers are composed into readable text server-side).
    user_message: MessageOut
    message: MessageOut
    tokens_used: int
    tokens_remaining: int | None
