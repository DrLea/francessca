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
    # 50 in + 20 out for the chat reply, and nothing more: the message
    # mentions no date or scheduled thing, so timeline extraction is skipped
    # before it costs a call.
    assert body["tokens_used"] == 70
    assert body["tokens_remaining"] == 100_000 - 70

    # A message that does mention something scheduled pays for the extra
    # extraction call.
    second = client.post(
        "/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "Tomorrow I have an appointment at the Ausländerbehörde."},
    )
    assert second.json()["tokens_used"] == 70 + 140


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


def test_chat_returns_structured_questions_and_accepts_a_batch_of_answers(
    client, db_session, monkeypatch
):
    from tests.conftest import FakeAI

    reply = (
        "I need two details before I can help.\n\n"
        '<questions>[{"question": "When were you dismissed?", '
        '"choices": ["This week", "Earlier"]}, '
        '{"question": "Was it in writing?", "choices": ["Yes", "No"]}]</questions>'
    )
    # Count the chat completions (the best-effort timeline extraction uses
    # the same fake, but only chat turns carry the question protocol).
    chat_calls: list[str] = []

    class CountingAI(FakeAI):
        def complete(self, *, system_prompt, messages, max_tokens=1024):  # noqa: ANN001
            if "<questions>" in system_prompt:
                chat_calls.append(system_prompt)
            return super().complete(
                system_prompt=system_prompt, messages=messages, max_tokens=max_tokens
            )

    monkeypatch.setattr(
        "app.services.chat_service.AIService", lambda *a, **k: CountingAI(reply)
    )
    token = _register(client, email="questions@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post("/chat", headers=headers, json={"message": "I was fired."})
    assert first.status_code == 200, first.text
    body = first.json()
    # The raw block never reaches the user; it comes back structured instead.
    assert "<questions>" not in body["message"]["content"]
    assert body["message"]["content"].endswith("before I can help.")
    questions = body["message"]["questions"]
    assert [q["question"] for q in questions] == [
        "When were you dismissed?",
        "Was it in writing?",
    ]
    assert questions[0]["choices"] == ["This week", "Earlier"]

    conv_id = body["conversation_id"]

    # The whole batch of answers goes back as ONE request / one user turn.
    second = client.post(
        "/chat",
        headers=headers,
        json={
            "conversation_id": conv_id,
            "answers": [
                {"question": "When were you dismissed?", "answer": "This week"},
                {"question": "Was it in writing?", "answer": None},
            ],
        },
    )
    assert second.status_code == 200, second.text
    user_turn = second.json()["user_message"]["content"]
    assert "This week" in user_turn and "(skipped)" in user_turn
    # Two questions answered, still one model call for the turn — two turns
    # in total, exactly as many as two plain typed messages would have cost.
    assert len(chat_calls) == 2

    detail = client.get(f"/chat/{conv_id}", headers=headers).json()
    # user, assistant(+questions), user(answers), assistant
    assert len(detail["messages"]) == 4
    assert detail["messages"][1]["questions"][0]["choices"] == ["This week", "Earlier"]
    assert detail["messages"][2]["questions"] == []


def test_chat_rejects_an_empty_turn(client, monkeypatch):
    from tests.conftest import FakeAI

    monkeypatch.setattr(
        "app.services.chat_service.AIService", lambda *a, **k: FakeAI()
    )
    token = _register(client, email="empty@example.com")
    resp = client.post(
        "/chat", headers={"Authorization": f"Bearer {token}"}, json={"message": "  "}
    )
    assert resp.status_code == 422


def test_timeline_lists_only_dated_entries_and_deletes_them(client, db_session):
    from datetime import date

    from app.models.timeline_event import TimelineEvent, TimelineSourceType

    token = _register(client, email="timeline@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    user_id = client.get("/me", headers=headers).json()["id"]

    db_session.add_all(
        [
            TimelineEvent(
                user_id=user_id,
                event_date=date(2026, 8, 31),
                date_label="31.08.2026",
                description="Appointment at the Ausländerbehörde.",
                source_type=TimelineSourceType.document,
                source_id=999,  # a document that no longer exists
            ),
            # A leftover row from the old, looser extractor.
            TimelineEvent(
                user_id=user_id,
                event_date=None,
                date_label="at termination",
                description="User was terminated from employment.",
                source_type=TimelineSourceType.message,
                source_id=1,
            ),
        ]
    )
    db_session.commit()

    rows = client.get("/case/timeline", headers=headers).json()
    assert len(rows) == 1
    assert rows[0]["event_date"] == "2026-08-31"
    # The source is gone, so the entry is simply unlinked rather than broken.
    assert rows[0]["source_label"] is None

    event_id = rows[0]["id"]
    assert client.delete(f"/case/timeline/{event_id}", headers=headers).status_code == 204
    assert client.get("/case/timeline", headers=headers).json() == []
    assert client.delete(f"/case/timeline/{event_id}", headers=headers).status_code == 404


def test_timeline_entries_can_be_added_by_hand(client):
    token = _register(client, email="manual@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/case/timeline",
        headers=headers,
        json={
            "event_date": "2030-12-12",
            "description": "Passport expires.",
            "is_deadline": True,
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["source_type"] == "manual"

    rows = client.get("/case/timeline", headers=headers).json()
    assert [r["description"] for r in rows] == ["Passport expires."]
    assert rows[0]["is_deadline"] is True
