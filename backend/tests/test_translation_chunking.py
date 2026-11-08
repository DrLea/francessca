"""Document translation is split into small calls.

A whole document in one request is what broke against a local model: it
overruns the context window and takes longer than any sane timeout.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.ai_service import AIResult
from app.services.file_service import (
    MAX_TRANSLATION_CHUNKS,
    TRANSLATION_CHUNK_CHARS,
    FileService,
    split_for_translation,
)
from app.models.document import Document
from app.models.user import User, UserRole, UserTier


def test_paragraphs_are_packed_up_to_the_budget():
    text = "\n\n".join(["Para one." * 20, "Para two." * 20, "Short."])
    chunks = split_for_translation(text)
    assert chunks
    assert all(len(c) <= TRANSLATION_CHUNK_CHARS for c in chunks)
    # Nothing is lost or duplicated.
    joined = " ".join(chunks).replace("\n\n", " ")
    for fragment in ("Para one.", "Para two.", "Short."):
        assert fragment in joined


def test_a_single_huge_paragraph_is_cut_at_whitespace():
    text = " ".join(["wort"] * 2000)
    chunks = split_for_translation(text)
    assert len(chunks) > 1
    assert all(len(c) <= TRANSLATION_CHUNK_CHARS for c in chunks)
    # No word was sliced in half.
    assert all(part == "wort" for chunk in chunks for part in chunk.split())


def test_empty_and_whitespace_text_yield_nothing():
    assert split_for_translation("") == []
    assert split_for_translation("\n\n   \n") == []


class _CountingAI:
    """Records how many calls a translation makes and how big each one is."""

    def __init__(self) -> None:
        self.model = "fake-local"
        self.calls: list[int] = []

    def complete(self, *, system_prompt, messages, max_tokens=1024):  # noqa: ANN001
        content = messages[0]["content"]
        self.calls.append(len(content))
        return AIResult(
            text="[uebersetzt] " + content[-20:],
            input_tokens=10,
            output_tokens=5,
            model=self.model,
        )


def _user(db_session) -> User:
    user = User(
        email="tr@example.com", password_hash="x", role=UserRole.user,
        tier=UserTier.free, token_limit=1_000_000, tokens_used=0,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _document(db_session, user: User, text: str) -> Document:
    doc = Document(
        user_id=user.id, filename="letter.pdf", stored_path="/tmp/letter.pdf",
        size=len(text), mime="application/pdf", extracted_text=text,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc


@pytest.fixture()
def uploads(tmp_path, monkeypatch):
    """FileService creates its upload directory on construction; keep that
    out of the real /data during tests."""
    from app.config import settings

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    return tmp_path


def test_translation_makes_one_small_call_per_chunk(db_session, uploads):
    user = _user(db_session)
    text = "\n\n".join([f"Absatz {i}. " + "Text " * 60 for i in range(6)])
    doc = _document(db_session, user, text)

    ai = _CountingAI()
    filename, pdf = FileService(db_session, ai=ai).translate(user, doc.id, "de")

    assert len(ai.calls) == len(split_for_translation(text)) > 1
    # Every request stays small enough for a 4k-token context window.
    assert max(ai.calls) < TRANSLATION_CHUNK_CHARS + 500
    assert filename == "letter_de.pdf"
    assert pdf.startswith(b"%PDF")


def test_an_over_long_document_is_refused_with_a_clear_message(db_session, uploads):
    user = _user(db_session)
    text = "\n\n".join(["Absatz. " * 150 for _ in range(MAX_TRANSLATION_CHUNKS + 5)])
    doc = _document(db_session, user, text)

    with pytest.raises(HTTPException) as excinfo:
        FileService(db_session, ai=_CountingAI()).translate(user, doc.id, "de")
    assert excinfo.value.status_code == 413
    assert "too long" in excinfo.value.detail
