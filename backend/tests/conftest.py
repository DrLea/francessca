"""Pytest fixtures: in-memory DB, app client, fake AI service."""
from __future__ import annotations

import os

# Configure env BEFORE importing app modules so Settings validates.
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret-please-change")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.database as database
from app.database import Base
import app.models  # noqa: F401  (register models)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # SQLite needs FK enforcement enabled explicitly.
    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_con, _):  # noqa: ANN001
        dbapi_con.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, future=True)

    # Point the app's SessionLocal/engine at the test database.
    database.engine = engine
    database.SessionLocal = TestingSession

    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


class FakeAI:
    """Deterministic stand-in for AIService (no network)."""

    def __init__(self, reply: str = "Thanks. Which country are you in?") -> None:
        self.reply = reply
        self.model = "fake-haiku"

    def complete(self, *, system_prompt, messages, max_tokens=1024):  # noqa: ANN001
        from app.services.ai_service import AIResult

        assert "Francessca" in system_prompt  # guardrail prompt always present
        return AIResult(
            text=self.reply, input_tokens=50, output_tokens=20, model=self.model
        )


@pytest.fixture()
def client(db_session):
    from app.database import get_db
    from app.main import app

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
