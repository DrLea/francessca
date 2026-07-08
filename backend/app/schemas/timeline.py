"""Timeline event schemas."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.timeline_event import TimelineSourceType


class TimelineEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_date: date | None
    date_label: str
    description: str
    is_deadline: bool
    source_type: TimelineSourceType
    source_id: int | None
    created_at: datetime
