"""Timeline event repository."""
from __future__ import annotations

from sqlalchemy import select

from app.models.timeline_event import TimelineEvent
from app.repositories.base import BaseRepository


class TimelineRepository(BaseRepository[TimelineEvent]):
    model = TimelineEvent

    def list_for_user(self, user_id: int) -> list[TimelineEvent]:
        """Dated events first (chronological), undated ones last."""
        return list(
            self.db.scalars(
                select(TimelineEvent)
                .where(TimelineEvent.user_id == user_id)
                .order_by(
                    TimelineEvent.event_date.is_(None),
                    TimelineEvent.event_date,
                    TimelineEvent.created_at,
                )
            )
        )
