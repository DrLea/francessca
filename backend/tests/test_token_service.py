"""Tests for token estimation and limit enforcement."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.models.user import User, UserTier
from app.services.token_service import TokenService, estimate_tokens


def test_estimate_tokens_scales_with_length():
    assert estimate_tokens("") == 0
    assert estimate_tokens("a" * 40) == 10


def test_fair_use_cap_blocks_within_24h(db_session):
    user = User(email="u@example.com", tier=UserTier.free, token_limit=100, tokens_used=0)
    db_session.add(user)
    db_session.flush()
    svc = TokenService(db_session)
    svc.record(user, input_tokens=60, output_tokens=30, model="x")
    db_session.flush()
    assert svc.used_today(user) == 90
    assert svc.remaining(user) == 10
    with pytest.raises(HTTPException) as exc:
        svc.ensure_within_limit(user, estimated=50)
    assert exc.value.status_code == 429


def test_default_cap_applies_when_no_override(db_session):
    from app.config import settings

    user = User(email="d@example.com", tier=UserTier.free, token_limit=None)
    db_session.add(user)
    db_session.flush()
    assert TokenService(db_session).daily_limit(user) == settings.fair_use_daily_tokens


def test_unlimited_premium_never_blocked(db_session):
    user = User(email="p@example.com", tier=UserTier.premium, token_limit=50)
    db_session.add(user)
    db_session.flush()
    svc = TokenService(db_session)
    assert svc.remaining(user) is None
    svc.ensure_within_limit(user, estimated=10_000_000)  # no raise


def test_record_increments_usage(db_session):
    user = User(email="r@example.com", tier=UserTier.free, token_limit=1000, tokens_used=0)
    db_session.add(user)
    db_session.flush()
    svc = TokenService(db_session)
    total = svc.record(user, input_tokens=30, output_tokens=20, model="x")
    assert total == 50
    assert user.tokens_used == 50
