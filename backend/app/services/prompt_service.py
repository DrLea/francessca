"""Resolves the active system prompt (DB-backed, with constant fallback)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.prompts import FRANCESSCA_SYSTEM_PROMPT
from app.models.prompt_version import PromptVersion


class PromptService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def active_system_prompt(self) -> str:
        """Return the active prompt from DB, else the immutable constant.

        The constant in app.core.prompts is the source of truth / fallback so
        the mandatory guardrails always apply even if the DB has no active row.
        """
        row = self.db.scalar(
            select(PromptVersion).where(PromptVersion.is_active.is_(True))
        )
        return row.content if row and row.content.strip() else FRANCESSCA_SYSTEM_PROMPT
