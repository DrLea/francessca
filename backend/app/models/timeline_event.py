"""Timeline event model.

Timeline events are facts with a date (or approximate date) that Francessca
automatically extracts from uploaded documents and chat messages — the
chronological "case timeline" that would otherwise have to be assembled by
hand. Extraction is best-effort and never contains legal conclusions, only
factual, dated statements the user already provided.
"""
from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TimelineSourceType(str, enum.Enum):
    document = "document"
    message = "message"
    manual = "manual"


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )

    # The resolved calendar date, when the extractor could pin one down.
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # The original date phrase (e.g. "mid-March 2026"), always populated —
    # used to display/sort events whose exact date is only approximate.
    date_label: Mapped[str] = mapped_column(String(128), default="")

    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_deadline: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    source_type: Mapped[TimelineSourceType] = mapped_column(
        Enum(TimelineSourceType, name="timeline_source_type"), nullable=False
    )
    # id of the Document or Message this event was extracted from.
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="timeline_events")
