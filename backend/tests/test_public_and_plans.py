"""Landing-page endpoints: public lawyer preview, lawyer sign-up, plans."""
from __future__ import annotations

from app.seeds.lawyers import sample_lawyers
from app.services.lawyer_service import LawyerService

APPLICATION = {
    "name": "Dr. Mara Lenz",
    "email": "Mara@Lenz-Recht.de",
    "law_firm": "Lenz Recht",
    "city": "München",
    "phone": "+49 89 111111",
    "specializations": ["Employment", "  Immigration  ", ""],
    "languages": ["German", "English"],
    "message": "I would like to be listed.",
}


def _register(client, email="user@example.com", **extra):
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "full_name": "Test", **extra},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def _admin_token(client, db_session):
    from app.models.user import User, UserRole

    token = _register(client, email="admin@example.com")
    user = db_session.query(User).filter(User.email == "admin@example.com").one()
    user.role = UserRole.admin
    db_session.commit()
    return token


def test_public_preview_hides_contact_details(client, db_session):
    LawyerService(db_session).sync_from_parsed(sample_lawyers())
    db_session.commit()

    resp = client.get("/public/lawyers?limit=3")
    assert resp.status_code == 200  # no auth header at all
    body = resp.json()
    assert body["total"] >= 3
    assert len(body["items"]) == 3
    first = body["items"][0]
    assert first["name"]
    assert "email" not in first and "phone" not in first


def test_lawyer_application_is_pending_until_an_admin_approves(client, db_session):
    created = client.post("/public/lawyer-applications", json=APPLICATION)
    assert created.status_code == 201, created.text
    application = created.json()
    assert application["status"] == "pending"
    assert application["email"] == "mara@lenz-recht.de"  # normalised
    assert application["specializations"] == ["Employment", "Immigration"]

    # Nothing is published yet.
    assert client.get("/public/lawyers").json()["total"] == 0

    token = _admin_token(client, db_session)
    headers = {"Authorization": f"Bearer {token}"}
    pending = client.get(
        "/admin/lawyer-applications?status_filter=pending", headers=headers
    ).json()
    assert [a["id"] for a in pending] == [application["id"]]

    approved = client.post(
        f"/admin/lawyer-applications/{application['id']}/approve", headers=headers
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert approved.json()["lawyer_id"]

    listed = client.get("/public/lawyers").json()
    assert [item["name"] for item in listed["items"]] == ["Dr. Mara Lenz"]
    assert listed["items"][0]["specializations"] == ["Employment", "Immigration"]

    # Reviewing it twice is a conflict, not a second directory entry.
    again = client.post(
        f"/admin/lawyer-applications/{application['id']}/approve", headers=headers
    )
    assert again.status_code == 409


def test_rejected_applications_never_reach_the_directory(client, db_session):
    application = client.post("/public/lawyer-applications", json=APPLICATION).json()
    headers = {"Authorization": f"Bearer {_admin_token(client, db_session)}"}
    rejected = client.post(
        f"/admin/lawyer-applications/{application['id']}/reject", headers=headers
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert client.get("/public/lawyers").json()["total"] == 0


def test_application_requires_a_real_email(client):
    bad = client.post(
        "/public/lawyer-applications", json={"name": "X Y", "email": "not-an-email"}
    )
    assert bad.status_code == 422


def test_plan_switch_is_free_during_beta(client):
    token = _register(client, email="plan@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/me", headers=headers).json()["tier"] == "free"

    upgraded = client.post("/me/plan", headers=headers, json={"tier": "premium"})
    assert upgraded.status_code == 200, upgraded.text
    assert upgraded.json()["tier"] == "premium"
    assert upgraded.json()["token_limit"] is None  # unlimited

    back = client.post("/me/plan", headers=headers, json={"tier": "free"})
    assert back.json()["tier"] == "free"
    assert back.json()["token_limit"] == 100_000


def test_plan_switch_requires_a_login(client):
    assert client.post("/me/plan", json={"tier": "premium"}).status_code == 401


def test_local_ai_service_speaks_openai_chat_completions(monkeypatch):
    """The offline build talks to a llama.cpp server on localhost; nothing
    about the prompt handling changes, only the wire format."""
    import httpx

    from app.services.ai_service import LocalAIService

    captured: dict = {}

    class _Resp:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "model": "qwen2.5-3b-instruct",
                "choices": [{"message": {"role": "assistant", "content": "Hallo."}}],
                "usage": {"prompt_tokens": 11, "completion_tokens": 3},
            }

    def _fake_post(url, json=None, timeout=None):  # noqa: ANN001
        captured["url"] = url
        captured["json"] = json
        return _Resp()

    monkeypatch.setattr(httpx, "post", _fake_post)
    service = LocalAIService(base_url="http://127.0.0.1:8757/v1", model="local")
    result = service.complete(
        system_prompt="You are Francessca.",
        messages=[{"role": "user", "content": "Hallo"}],
        max_tokens=256,
    )

    assert captured["url"] == "http://127.0.0.1:8757/v1/chat/completions"
    # The system prompt stays in its own turn, exactly as with the hosted API.
    assert captured["json"]["messages"][0] == {
        "role": "system",
        "content": "You are Francessca.",
    }
    assert result.text == "Hallo."
    assert (result.input_tokens, result.output_tokens) == (11, 3)


def test_provider_factory_follows_the_setting(monkeypatch):
    from app.config import settings
    from app.services.ai_service import AIService, LocalAIService, build_ai_service

    monkeypatch.setattr(settings, "ai_provider", "local")
    assert isinstance(build_ai_service(), LocalAIService)
    monkeypatch.setattr(settings, "ai_provider", "anthropic")
    assert isinstance(build_ai_service(), AIService)


def test_reasoning_models_do_not_leak_their_scratch_work(monkeypatch):
    """Qwen3 and friends answer with a <think> block first. It must never
    reach the transcript, the timeline, or the next turn's context."""
    import httpx

    from app.services.ai_service import LocalAIService, strip_reasoning

    assert strip_reasoning("<think>hmm, dismissal?</think>\n\nI'm sorry.") == "I'm sorry."
    # Truncated mid-thought: everything from the tag on is scratch work.
    assert strip_reasoning("Answer.\n<think>still going") == "Answer."
    assert strip_reasoning("No reasoning here.") == "No reasoning here."

    class _Resp:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "model": "qwen3:8b",
                "choices": [
                    {
                        "message": {
                            "content": "<think>The user was dismissed...</think>\n"
                            "I'm sorry to hear that."
                        }
                    }
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 9},
            }

    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp())
    result = LocalAIService().complete(system_prompt="x", messages=[])
    assert result.text == "I'm sorry to hear that."


def test_desktop_downloads_are_runtime_config(client, monkeypatch):
    """Publishing a new build is a config change plus a restart -- no
    frontend rebuild, which is what baking the URLs in would have required."""
    from app.config import settings

    empty = client.get("/public/downloads")
    assert empty.status_code == 200  # public: a visitor is not signed in
    assert empty.json() == {"version": None, "items": []}

    monkeypatch.setattr(settings, "download_version", "0.1.0")
    monkeypatch.setattr(settings, "download_windows", "https://example.com/F.exe ")
    monkeypatch.setattr(settings, "download_windows_sha256", "abc123")
    monkeypatch.setattr(settings, "download_linux", "https://example.com/F-linux")

    body = client.get("/public/downloads").json()
    assert body["version"] == "0.1.0"
    assert body["items"] == [
        {
            "platform": "windows",
            "url": "https://example.com/F.exe",
            "sha256": "abc123",
        },
        {"platform": "linux", "url": "https://example.com/F-linux", "sha256": None},
    ]


def test_a_locally_hosted_build_is_served_and_hashed(client, tmp_path, monkeypatch):
    """Self-hosting matters where a third-party CDN is unreachable: the file
    is offered on the app's own domain, and its checksum is computed here."""
    import hashlib

    from app.config import settings

    exe = tmp_path / "Francessca.exe"
    exe.write_bytes(b"MZ fake windows build")
    monkeypatch.setattr(settings, "download_dir", str(tmp_path))
    # A configured external URL loses to the local copy.
    monkeypatch.setattr(settings, "download_windows", "https://example.com/F.exe")

    body = client.get("/public/downloads").json()
    assert body["items"] == [
        {
            "platform": "windows",
            "url": "/public/download/windows",
            "sha256": hashlib.sha256(b"MZ fake windows build").hexdigest(),
        }
    ]

    got = client.get("/public/download/windows")
    assert got.status_code == 200
    assert got.content == b"MZ fake windows build"
    assert "Francessca.exe" in got.headers["content-disposition"]


def test_downloads_reject_anything_but_the_known_platforms(client, tmp_path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "download_dir", str(tmp_path))
    # No traversal: the filename never comes from the request.
    assert client.get("/public/download/..%2F..%2Fetc%2Fpasswd").status_code == 404
    assert client.get("/public/download/windows").status_code == 404  # nothing published
