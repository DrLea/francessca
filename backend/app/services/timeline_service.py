"""AI-assisted extraction of dated facts into a per-user case timeline.

This is the "smart timeline" feature: instead of asking the user to build a
chronology by hand, Francessca reads every uploaded document and chat
message and pulls out concrete, dated events (a termination, a notice, a
missed deadline, a meeting) into structured `TimelineEvent` rows.

Extraction is strictly best-effort:
- it reuses the mandatory Francessca system prompt, so the same "no legal
  advice / no predictions" guardrails apply to this call as to any other;
- it never invents facts — only events actually stated in the text;
- it never raises. A failure (bad JSON, no budget left, network error) is
  logged and simply results in zero new events, so it can never break the
  upload or chat flow that triggers it.
"""
from __future__ import annotations

import json
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.timeline_event import TimelineEvent, TimelineSourceType
from app.models.user import User
from app.repositories.timeline_repo import TimelineRepository
from app.services.ai_service import AIService
from app.services.prompt_service import PromptService
from app.services.token_service import TokenService, estimate_tokens

log = get_logger("francessca.timeline")

# Skip trivially short text — not worth an AI call and unlikely to contain a
# datable fact.
_MIN_LENGTH = 20

_EXTRACTION_INSTRUCTION = """From the text below, extract every concrete, dated (or datable) \
factual event that would matter to a lawyer preparing this case — for example a termination, \
a notice received, a missed payment, a signed contract, a meeting, or a deadline the user must \
act within.

Return a JSON array. Each item must have exactly these keys:
- "date": an ISO date "YYYY-MM-DD" if a specific date is stated or can be clearly inferred, \
else null
- "date_label": the date phrase as written, or a short human label if only approximate \
(e.g. "mid-March 2026", "the day after signing")
- "description": one short factual sentence describing what happened — no legal conclusions, \
no advice, no predictions
- "is_deadline": true only if this date represents a deadline or time limit the user must act \
within

Only include events that are actually stated or clearly implied by the text — never invent a \
date or event. If nothing datable is present, return an empty array [].
Output ONLY the JSON array. No prose, no code fences."""


class TimelineService:
    def __init__(self, db: Session, ai: AIService | None = None) -> None:
        self.db = db
        self.events = TimelineRepository(db)
        self.prompts = PromptService(db)
        self.tokens = TokenService(db)
        self.ai = ai or AIService()

    def list_for_user(self, user_id: int) -> list[TimelineEvent]:
        return self.events.list_for_user(user_id)

    def extract_from_text(
        self,
        user: User,
        text: str | None,
        *,
        source_type: TimelineSourceType,
        source_id: int | None,
        conversation_id: int | None = None,
    ) -> list[TimelineEvent]:
        """Best-effort extraction. Flushes new rows but does not commit —
        the caller (chat/file service) owns the transaction boundary."""
        text = (text or "").strip()
        if len(text) < _MIN_LENGTH:
            return []

        try:
            estimated = estimate_tokens(text) + 300
            if not user.is_unlimited and estimated > (self.tokens.remaining(user) or 0):
                log.info("timeline extraction skipped: token budget exhausted")
                return []

            result = self.ai.complete(
                system_prompt=self.prompts.active_system_prompt(),
                messages=[
                    {
                        "role": "user",
                        "content": f"{_EXTRACTION_INSTRUCTION}\n\nText:\n{text}",
                    }
                ],
                max_tokens=800,
            )
            self.tokens.record(
                user,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                model=result.model,
                conversation_id=conversation_id,
            )
            items = self._parse(result.text)
        except Exception as exc:  # noqa: BLE001 - extraction must never break the caller
            log.warning("timeline extraction failed: %s", exc)
            return []

        created: list[TimelineEvent] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            description = str(item.get("description") or "").strip()[:2000]
            if not description:
                continue
            event = TimelineEvent(
                user_id=user.id,
                conversation_id=conversation_id,
                event_date=self._parse_date(item.get("date")),
                date_label=str(item.get("date_label") or "")[:128],
                description=description,
                is_deadline=bool(item.get("is_deadline")),
                source_type=source_type,
                source_id=source_id,
            )
            self.events.add(event)
            created.append(event)
        return created

    @staticmethod
    def _parse(raw: str) -> list:
        """Parse the model's JSON array, tolerating code fences and stray prose."""
        text = raw.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        start, end = text.find("["), text.rfind("]")
        if start == -1 or end == -1:
            return []
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            log.warning("could not parse timeline extraction JSON")
            return []
        return data if isinstance(data, list) else []

    @staticmethod
    def _parse_date(value: object) -> date | None:
        if not value or not isinstance(value, str):
            return None
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
