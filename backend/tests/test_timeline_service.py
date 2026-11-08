"""Tests for AI-based timeline extraction.

The timeline is a calendar, not a chronology: only entries with a real day
and a real calendar kind (appointment, hearing, meeting, deadline, expiry,
payment, submission) are allowed in.
"""
from __future__ import annotations

from datetime import date, timedelta

from app.models.timeline_event import TimelineSourceType
from app.models.user import User, UserRole, UserTier
from app.services.ai_service import AIResult
from app.services.timeline_service import TimelineService, looks_scheduling_related


class _FakeAI:
    """Returns a fixed, well-formed extraction response (unlike the chat
    FakeAI, which returns plain prose)."""

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.model = "fake-haiku"
        self.calls = 0

    def complete(self, *, system_prompt, messages, max_tokens=1024):  # noqa: ANN001
        assert "Francessca" in system_prompt
        self.calls += 1
        return AIResult(text=self.reply, input_tokens=40, output_tokens=15, model=self.model)


def _make_user(db_session) -> User:
    user = User(
        email="tl@example.com",
        password_hash="x",
        role=UserRole.user,
        tier=UserTier.free,
        token_limit=100_000,
        tokens_used=0,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_keeps_dated_calendar_entries(db_session):
    reply = """[
        {"date": "2026-08-31", "kind": "appointment", "date_label": "31.08.2026",
         "description": "Appointment at the Ausländerbehörde."},
        {"date": "2030-12-12", "kind": "expiry", "date_label": "12.12.2030",
         "description": "Passport expires."}
    ]"""
    user = _make_user(db_session)
    service = TimelineService(db_session, ai=_FakeAI(reply))

    events = service.extract_from_text(
        user,
        "My appointment is on 31.08.2026 and my passport expires 12.12.2030.",
        source_type=TimelineSourceType.document,
        source_id=1,
    )
    db_session.commit()

    assert [e.event_date.isoformat() for e in events] == ["2026-08-31", "2030-12-12"]
    assert events[0].is_deadline is False  # appointment
    assert events[1].is_deadline is True  # expiry
    assert len(service.list_for_user(user.id)) == 2


def test_drops_undated_and_narrative_entries(db_session):
    """The old extractor produced rows like "at termination" / "during 1 to 5
    year period". Neither a missing date nor an unknown kind gets through."""
    reply = """[
        {"date": null, "kind": "deadline", "date_label": "within three weeks",
         "description": "Deadline to file a claim."},
        {"date": "2026-08-27", "kind": "termination", "date_label": "yesterday",
         "description": "User was terminated from employment."},
        {"date": "not-a-date", "kind": "appointment", "date_label": "at termination",
         "description": "Client relationship ended."},
        {"date": "2026-09-10", "kind": "hearing", "date_label": "10 September",
         "description": "Labour court hearing."}
    ]"""
    user = _make_user(db_session)
    service = TimelineService(db_session, ai=_FakeAI(reply))

    events = service.extract_from_text(
        user,
        "I was fired yesterday, the hearing is on 10 September.",
        source_type=TimelineSourceType.document,
        source_id=1,
    )
    db_session.commit()

    assert len(events) == 1
    assert events[0].description == "Labour court hearing."


def test_identical_entry_is_not_filed_twice(db_session):
    reply = """[{"date": "2026-08-31", "kind": "appointment", "date_label": "31.08.2026",
                 "description": "Appointment at the Ausländerbehörde."}]"""
    user = _make_user(db_session)
    service = TimelineService(db_session, ai=_FakeAI(reply))
    text = "Appointment at the Ausländerbehörde on 31.08.2026."

    service.extract_from_text(
        user, text, source_type=TimelineSourceType.document, source_id=1
    )
    db_session.commit()
    again = service.extract_from_text(
        user, text, source_type=TimelineSourceType.message, source_id=2
    )
    db_session.commit()

    assert again == []
    assert len(service.list_for_user(user.id)) == 1


def test_chat_messages_without_a_date_hint_never_reach_the_model(db_session):
    user = _make_user(db_session)
    ai = _FakeAI("[]")
    service = TimelineService(db_session, ai=ai)

    assert service.extract_from_text(
        user,
        "I feel that my employer treated me unfairly and I am upset about it.",
        source_type=TimelineSourceType.message,
        source_id=1,
    ) == []
    assert ai.calls == 0

    # A scheduling word is enough to make it worth a call.
    service.extract_from_text(
        user,
        "Ahh tomorrow I have a meeting with my former employer about this.",
        source_type=TimelineSourceType.message,
        source_id=2,
    )
    assert ai.calls == 1

    # ...and documents are always scanned, hint or not.
    service.extract_from_text(
        user,
        "A letter with no obvious scheduling words in it whatsoever.",
        source_type=TimelineSourceType.document,
        source_id=3,
    )
    assert ai.calls == 2


def test_schedule_hint_detection():
    assert looks_scheduling_related("Termin am 31.08.2026")
    assert looks_scheduling_related("завтра встреча с адвокатом")
    assert looks_scheduling_related("ahh tomorrow I have meeting")
    assert not looks_scheduling_related("my boss was very rude to me and I left")


def test_deletes_only_the_owner_s_event(db_session):
    reply = """[{"date": "2026-08-31", "kind": "appointment", "date_label": "31.08.2026",
                 "description": "Appointment at the Ausländerbehörde."}]"""
    user = _make_user(db_session)
    service = TimelineService(db_session, ai=_FakeAI(reply))
    events = service.extract_from_text(
        user, "Appointment on 31.08.2026.", source_type=TimelineSourceType.document,
        source_id=1,
    )
    db_session.commit()
    event_id = events[0].id

    assert service.delete_for_user(event_id, user_id=user.id + 999) is False
    assert service.delete_for_user(event_id, user_id=user.id) is True
    assert service.list_for_user(user.id) == []


def test_extract_from_text_skips_short_text(db_session):
    user = _make_user(db_session)
    service = TimelineService(db_session, ai=_FakeAI("[]"))
    assert service.extract_from_text(
        user, "ok", source_type=TimelineSourceType.message, source_id=1
    ) == []


def test_extract_from_text_tolerates_bad_json(db_session):
    user = _make_user(db_session)
    service = TimelineService(db_session, ai=_FakeAI("not json at all, sorry"))
    events = service.extract_from_text(
        user,
        "Something happened on 3 March but the model replied badly.",
        source_type=TimelineSourceType.document,
        source_id=1,
    )
    assert events == []


def test_relative_dates_are_resolved_by_the_model_against_today(db_session):
    """The instruction carries today's date so 'tomorrow' can come back as a
    real day — the service itself only validates what it gets."""
    tomorrow = date.today() + timedelta(days=1)
    reply = (
        f'[{{"date": "{tomorrow.isoformat()}", "kind": "meeting", '
        f'"date_label": "tomorrow", "description": "Meeting with the employer."}}]'
    )
    user = _make_user(db_session)
    ai = _FakeAI(reply)
    service = TimelineService(db_session, ai=ai)
    events = service.extract_from_text(
        user,
        "Ahh tomorrow I have a meeting with my employer.",
        source_type=TimelineSourceType.message,
        source_id=1,
    )
    db_session.commit()
    assert events[0].event_date == tomorrow


def test_explicit_timeline_request_reaches_the_model_with_context(db_session):
    """"add it to my timeline" carries no date of its own — the previous
    assistant turn is what makes it resolvable."""
    tomorrow = date.today() + timedelta(days=1)
    reply = (
        f'[{{"date": "{tomorrow.isoformat()}", "kind": "appointment", '
        f'"date_label": "tomorrow at 16:00", '
        f'"description": "Appointment with the lawyer at 16:00."}}]'
    )
    user = _make_user(db_session)
    ai = _FakeAI(reply)
    service = TimelineService(db_session, ai=ai)

    events = service.extract_from_text(
        user,
        "add it to my timeline",
        source_type=TimelineSourceType.message,
        source_id=1,
        context="You could book the consultation at 16:00 tomorrow.",
    )
    db_session.commit()

    assert ai.calls == 1
    assert events[0].event_date == tomorrow
    assert looks_scheduling_related("add it to my timeline")
    assert looks_scheduling_related("добавь в мой календарь")


def test_manual_entries_can_be_added_by_hand(db_session):
    user = _make_user(db_session)
    service = TimelineService(db_session, ai=_FakeAI("[]"))
    event = service.add_manual(
        user,
        event_date=date(2026, 8, 31),
        description="  Appointment at the Ausländerbehörde.  ",
        is_deadline=False,
    )
    assert event.source_type is TimelineSourceType.manual
    assert event.description == "Appointment at the Ausländerbehörde."
    assert [e.id for e in service.list_for_user(user.id)] == [event.id]
