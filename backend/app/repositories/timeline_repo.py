"""Timeline event repository."""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select

from app.models.timeline_event import TimelineEvent
from app.repositories.base import BaseRepository


class TimelineRepository(BaseRepository[TimelineEvent]):
    model = TimelineEvent

    def list_for_user(self, user_id: int) -> list[TimelineEvent]:
        """Chronological calendar entries.

        Only dated entries are returned: the timeline is a diary, and an
        entry without a day has nothing to sit on. This also hides rows left
        over from the earlier, looser extractor ("at termination", "during 1
        to 5 year period") without needing a data migration.
        """
        return list(
            self.db.scalars(
                select(TimelineEvent)
                .where(
                    TimelineEvent.user_id == user_id,
                    TimelineEvent.event_date.is_not(None),
                )
                .order_by(TimelineEvent.event_date, TimelineEvent.created_at)
            )
        )

    def get_for_user(self, event_id: int, user_id: int) -> TimelineEvent | None:
        return self.db.scalar(
            select(TimelineEvent).where(
                TimelineEvent.id == event_id, TimelineEvent.user_id == user_id
            )
        )

    def exists_similar(self, user_id: int, event_date: date, description: str) -> bool:
        """Guard against the same appointment being filed twice (mentioned in
        a document and again in chat, or simply repeated by the user)."""
        return (
            self.db.scalar(
                select(func.count())
                .select_from(TimelineEvent)
                .where(
                    TimelineEvent.user_id == user_id,
                    TimelineEvent.event_date == event_date,
                    func.lower(TimelineEvent.description) == description.strip().lower(),
                )
            )
            or 0
        ) > 0
