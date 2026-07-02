"""Case model — the structured summary produced for a lawyer."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Use JSONB on PostgreSQL (production) and fall back to JSON elsewhere (tests).
JSONType = JSON().with_variant(JSONB(), "postgresql")


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), default="Untitled case")
    case_type: Mapped[str | None] = mapped_column(String(64))

    # Structured summary stored as JSON. See schemas.case.CaseSummary.
    summary: Mapped[dict] = mapped_column(JSONType, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="cases")
    exports: Mapped[list["Export"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
