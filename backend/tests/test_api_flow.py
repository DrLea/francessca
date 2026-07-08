"""End-to-end API tests: register, chat (fake AI), lawyer search."""
from __future__ import annotations

from app.seeds.lawyers import sample_lawyers
from app.services.lawyer_service import LawyerService


def _register(client, email="user@example.com"):
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "full_name": "Test"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def test_register_login_me(client):
    token = _register(client)
    me = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"
    assert me.json()["token_limit"] == 100_000


def test_chat_uses_fake_ai_and_records_tokens(client, db_session, monkeypatch):
    from tests.conftest import FakeAI

    monkeypatch.setattr(
        "app.services.chat_service.AIService", lambda *a, **k: FakeAI()
    )
    token = _register(client)
    resp = client.post(
        "/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "I was fired yesterday."},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "country" in body["message"]["content"].lower()
    # 50 in + 20 out for the chat reply, plus another 50 in + 20 out for the
    # best-effort timeline-extraction call the FakeAI also answers.
    assert body["tokens_used"] == 140
    assert body["tokens_remaining"] == 100_000 - 140


def test_lawyer_search(client, db_session):
    LawyerService(db_session).sync_from_parsed(sample_lawyers())
    db_session.commit()
    token = _register(client, email="search@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/lawyers/search?specialization=Employment", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any("Employment" in lw["specializations"] for lw in data["items"])

    by_city = client.get("/lawyers/search?city=Augsburg", headers=headers)
    assert by_city.json()["total"] == 1


def test_unauthenticated_rejected(client):
    assert client.get("/me").status_code == 401
