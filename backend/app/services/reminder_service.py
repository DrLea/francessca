"""Deadline reminders: every dated entry in a user's timeline is reminded
7 days and 1 day before, by email (when SMTP is configured) and in the app
(GET /case/timeline/upcoming). Each reminder goes out once.

Run by a background loop started in app.main (hourly), or on demand by an
admin through POST /admin/reminders/run.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.logging import get_logger, log_event
from app.models.timeline_event import TimelineEvent
from app.services import email_service

log = get_logger("francessca.reminders")

# (days before, column that records it was sent)
WINDOWS = ((1, "reminded_1d_at"), (7, "reminded_7d_at"))


def send_due_reminders(db: Session, today: date | None = None) -> int:
    today = today or date.today()
    now = datetime.now(timezone.utc)
    events = db.scalars(
        select(TimelineEvent)
        .options(selectinload(TimelineEvent.user))
        .where(
            TimelineEvent.event_date.is_not(None),
            TimelineEvent.event_date >= today,
            TimelineEvent.event_date <= today + timedelta(days=7),
        )
    )
    sent = 0
    for event in events:
        days_left = (event.event_date - today).days
        for days, column in WINDOWS:
            if days_left <= days and getattr(event, column) is None:
                # One reminder per window; the 1-day one also covers the
                # 7-day one when an entry is added late.
                setattr(event, "reminded_7d_at", event.reminded_7d_at or now)
                setattr(event, column, now)
                if event.user is not None:
                    email_service.deadline_reminder(
                        event.user.email,
                        event.description,
                        event.event_date.strftime("%d.%m.%Y"),
                        days_left,
                    )
                sent += 1
                break
    db.commit()
    if sent:
        log_event(log, "reminders_sent", count=sent)
    return sent


async def reminder_loop(interval_seconds: int = 3600) -> None:
    """Background loop: check for due reminders every hour."""
    from app.database import SessionLocal

    while True:
        try:
            await asyncio.to_thread(_run_once, SessionLocal)
        except Exception:  # noqa: BLE001 - never kill the loop
            log.exception("reminder run failed")
        await asyncio.sleep(interval_seconds)


def _run_once(session_factory) -> None:  # noqa: ANN001
    db = session_factory()
    try:
        send_due_reminders(db)
    finally:
        db.close()
