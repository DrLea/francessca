"""Generates a structured case summary from a conversation using the AI.

The model is asked to return strict JSON matching CaseSummary. The mandatory
system prompt still applies (the model never gives legal advice — it only
organizes facts the user provided).
"""
from __future__ import annotations

import json

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.languages import document_language_instruction
from app.core.logging import get_logger
from app.models.case import Case
from app.models.message import MessageRole
from app.models.user import User
from app.repositories.conversation_repo import ConversationRepository, MessageRepository
from app.repositories.document_repo import CaseRepository, DocumentRepository
from app.schemas.case import CaseSummary
from app.services.ai_service import AIService
from app.services.prompt_service import PromptService
from app.services.timeline_service import TimelineService
from app.services.token_service import TokenService

log = get_logger("francessca.case")

_SUMMARY_INSTRUCTION = """Based ONLY on the facts the user has shared in this conversation,
produce a structured case summary as STRICT JSON with exactly these keys:
case_type (string), timeline (array of strings), people_involved (array),
important_dates (array), documents_available (array), missing_documents (array),
questions_for_lawyer (array), potential_relevant_topics (array),
generated_forms (array), attachments (array), narrative (string).
Do not give legal advice or predict outcomes. Output ONLY the JSON object, no prose."""


class CaseService:
    def __init__(self, db: Session, ai: AIService | None = None) -> None:
        self.db = db
        self.conversations = ConversationRepository(db)
        self.messages = MessageRepository(db)
        self.documents = DocumentRepository(db)
        self.cases = CaseRepository(db)
        self.prompts = PromptService(db)
        self.tokens = TokenService(db)
        self.timeline = TimelineService(db)
        self.ai = ai or AIService()

    def generate_summary(
        self, user: User, conversation_id: int, title: str | None
    ) -> Case:
        conv = self.conversations.get_for_user(conversation_id, user.id)
        if conv is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
            )

        history = self.messages.history(conv.id)
        transcript = "\n".join(
            f"{m.role.value.upper()}: {m.content}"
            for m in history
            if m.role in (MessageRole.user, MessageRole.assistant)
        )
        doc_names = [d.filename for d in self.documents.list_for_user(user.id)]

        # Feed in the already-extracted timeline as authoritative dated facts
        # so the model doesn't have to re-derive dates from free-form chat.
        events = self.timeline.list_for_user(user.id)
        timeline_context = "\n".join(
            f"- {e.event_date.isoformat() if e.event_date else e.date_label or 'undated'}: "
            f"{e.description}" + (" [DEADLINE]" if e.is_deadline else "")
            for e in events
        )

        model_messages = [
            {
                "role": "user",
                "content": (
                    f"Conversation transcript:\n{transcript}\n\n"
                    f"Uploaded documents: {', '.join(doc_names) or 'none'}\n\n"
                    f"Already-extracted timeline facts (use these dates as authoritative "
                    f"if referenced): \n{timeline_context or 'none'}\n\n"
                    f"{_SUMMARY_INSTRUCTION}"
                ),
            }
        ]
        result = self.ai.complete(
            system_prompt=self.prompts.active_system_prompt()
            + document_language_instruction(user.language),
            messages=model_messages,
            max_tokens=1500,
        )
        self.tokens.record(
            user,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            model=result.model,
            conversation_id=conv.id,
        )

        summary = self._parse_summary(result.text, doc_names)

        case = Case(
            user_id=user.id,
            conversation_id=conv.id,
            title=title or conv.title or "Untitled case",
            case_type=summary.case_type or None,
            summary=summary.model_dump(),
        )
        self.cases.add(case)
        self.db.commit()
        self.db.refresh(case)
        return case

    @staticmethod
    def _parse_summary(raw: str, doc_names: list[str]) -> CaseSummary:
        """Parse the model's JSON, tolerating code fences and stray prose."""
        text = raw.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1:
            data: dict = {"narrative": raw.strip()}
        else:
            try:
                data = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                log.warning("Could not parse case summary JSON; using fallback")
                data = {"narrative": raw.strip()}

        if not data.get("documents_available"):
            data["documents_available"] = doc_names
        data.setdefault("attachments", doc_names)
        return CaseSummary(
            **{k: v for k, v in data.items() if k in CaseSummary.model_fields}
        )
