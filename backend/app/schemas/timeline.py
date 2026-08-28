"""Timeline event schemas."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.timeline_event import TimelineSourceType


class TimelineEventCreate(BaseModel):
    """An entry the user adds by hand from the timeline page."""

    event_date: date
    description: str = Field(min_length=1, max_length=2_000)
    is_deadline: bool = False


class TimelineEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    # Always set: an entry without a calendar day is never returned.
    event_date: date
    date_label: str
    description: str
    is_deadline: bool

    source_type: TimelineSourceType
    # Document id for `document` entries, message id for `message` entries.
    source_id: int | None
    # Set for entries extracted from chat — the conversation to open.
    conversation_id: int | None = None
    # Filename or conversation title, so the client can label the link to
    # wherever this entry came from. None when the source has been deleted.
    source_label: str | None = None
