"""Tests for AI-based timeline extraction."""
from __future__ import annotations

from app.models.timeline_event import TimelineSourceType
from app.models.user import User, UserRole, UserTier
from app.services.ai_service import AIResult
from app.services.timeline_service import TimelineService


class _FakeAI:
    """Returns a fixed, well-formed extraction response (unlike the chat
    FakeAI, which returns plain prose)."""

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.model = "fake-haiku"

    def complete(self, *, system_prompt, messages, max_tokens=1024):  # noqa: ANN001
        assert "Francessca" in system_prompt
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


def test_extract_from_text_creates_events(db_session):
    reply = """[
        {"date": "2026-06-01", "date_label": "1 June 2026",
         "description": "User received a termination letter.", "is_deadline": false},
        {"date": null, "date_label": "within three weeks",
         "description": "Deadline to file a claim.", "is_deadline": true}
    ]"""
    user = _make_user(db_session)
    service = TimelineService(db_session, ai=_FakeAI(reply))

    events = service.extract_from_text(
        user,
        "I was fired on 1 June 2026 and need to respond quickly.",
        source_type=TimelineSourceType.message,
        source_id=1,
    )
    db_session.commit()

    assert len(events) == 2
    assert events[0].event_date.isoformat() == "2026-06-01"
    assert events[1].event_date is None
    assert events[1].is_deadline is True

    stored = service.list_for_user(user.id)
    assert len(stored) == 2


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
        "Something happened but the model replied badly.",
        source_type=TimelineSourceType.document,
        source_id=1,
    )
    assert events == []
