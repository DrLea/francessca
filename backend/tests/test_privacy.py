"""Encryption at rest, consent before storing, one-tap export and delete."""
from __future__ import annotations

import io
import json
import os
import zipfile

from sqlalchemy import text

from app.core.crypto import decrypt_bytes, encrypt_bytes, encrypt_text, decrypt_text


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register(client, email="p@example.com", consent=True) -> str:
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "data_consent": consent},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def test_roundtrip_and_legacy_plaintext():
    assert decrypt_bytes(encrypt_bytes(b"secret")) == b"secret"
    assert decrypt_bytes(b"old plain file") == b"old plain file"
    assert decrypt_text(encrypt_text("Ausländerbehörde")) == "Ausländerbehörde"
    assert decrypt_text("legacy") == "legacy"
    assert encrypt_bytes(b"x") != encrypt_bytes(b"x")  # random nonce


def test_nothing_is_stored_without_consent(client, monkeypatch):
    from tests.conftest import FakeAI

    monkeypatch.setattr("app.services.chat_service.build_ai_service", lambda *a, **k: FakeAI())
    token = _register(client, consent=False)
    blocked = client.post("/chat", headers=_auth(token), json={"message": "Hello"})
    assert blocked.status_code == 428
    assert client.post("/me/consent", headers=_auth(token)).json()["data_consent_at"]
    assert client.post("/chat", headers=_auth(token), json={"message": "Hello"}).status_code == 200


def test_messages_and_files_are_encrypted_at_rest(client, db_session, monkeypatch, tmp_path):
    from app.config import settings
    from tests.conftest import FakeAI

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    monkeypatch.setattr("app.services.chat_service.build_ai_service", lambda *a, **k: FakeAI())
    token = _register(client)
    client.post("/chat", headers=_auth(token), json={"message": "My landlord kept the deposit"})
    raw = db_session.execute(text("SELECT content FROM messages ORDER BY id LIMIT 1")).scalar()
    assert raw.startswith("enc1:") and "landlord" not in raw

    up = client.post(
        "/files", headers=_auth(token),
        files={"file": ("letter.txt", b"Frist bis 31.12.2026", "text/plain")},
    )
    assert up.status_code == 200, up.text
    stored = [p for p in tmp_path.rglob("*") if p.is_file()][0]
    assert b"Frist" not in stored.read_bytes()
    got = client.get(f"/files/{up.json()['id']}/download", headers=_auth(token))
    assert got.content == b"Frist bis 31.12.2026"


def test_export_and_delete_everything(client, monkeypatch, tmp_path):
    from app.config import settings
    from tests.conftest import FakeAI

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    monkeypatch.setattr("app.services.chat_service.build_ai_service", lambda *a, **k: FakeAI())
    token = _register(client)
    client.post("/chat", headers=_auth(token), json={"message": "Hello there"})
    client.post(
        "/files", headers=_auth(token),
        files={"file": ("note.txt", b"my note", "text/plain")},
    )
    export = client.get("/me/export", headers=_auth(token))
    assert export.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(export.content))
    data = json.loads(zf.read("francesca_data.json"))
    assert data["conversations"][0]["messages"][0]["content"] == "Hello there"
    assert any(name.endswith("note.txt") for name in zf.namelist())

    assert client.delete("/me", headers=_auth(token)).status_code == 200
    assert not [p for p in tmp_path.rglob("*") if p.is_file()]
    assert client.get("/me", headers=_auth(token)).status_code == 401


def test_german_reply_with_photo_evidence(client, monkeypatch, tmp_path):
    from PIL import Image as PILImage

    from app.config import settings
    from tests.conftest import FakeAI

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    reply = json.dumps({
        "subject": "Zimmer entspricht nicht dem Vertrag",
        "german": "Sehr geehrte Damen und Herren,\n\nanbei Fotos (Anlage 1).\n\nMit freundlichen Grüßen",
        "translation": "Dear Sir or Madam, ...",
    })
    monkeypatch.setattr(
        "app.services.reply_service.build_ai_service", lambda *a, **k: FakeAI(reply=reply)
    )
    token = _register(client)
    buf = io.BytesIO()
    PILImage.new("RGB", (40, 30), "red").save(buf, format="PNG")
    photo = client.post(
        "/files", headers=_auth(token), files={"file": ("room.png", buf.getvalue(), "image/png")}
    ).json()
    draft = client.post(
        "/case/reply-draft", headers=_auth(token),
        json={"situation": "The dorm room is not the one I paid for.",
              "evidence_document_ids": [photo["id"]]},
    )
    assert draft.status_code == 200, draft.text
    body = draft.json()
    assert body["german"].startswith("Sehr geehrte") and body["evidence"][0]["filename"] == "room.png"
    pdf = client.post(
        "/case/reply-draft/pdf", headers=_auth(token),
        json={"subject": body["subject"], "german": body["german"],
              "evidence_document_ids": [photo["id"]]},
    )
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
