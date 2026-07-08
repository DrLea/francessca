"""Chat orchestration: history, token gating, AI call, persistence."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.languages import language_instruction
from app.core.prompts import USER_CONTENT_GUARD
from app.models.conversation import Conversation
from app.models.message import Message, MessageRole
from app.models.timeline_event import TimelineSourceType
from app.models.user import User
from app.repositories.conversation_repo import (
    ConversationRepository,
    MessageRepository,
)
from app.repositories.document_repo import DocumentRepository
from app.schemas.chat import ChatRequest
from app.services.ai_service import AIResult, AIService
from app.services.prompt_service import PromptService
from app.services.timeline_service import TimelineService
from app.services.token_service import TokenService, estimate_tokens

# Keep the prompt context bounded: only send the most recent N turns.
_MAX_HISTORY = 20


class ChatService:
    def __init__(self, db: Session, ai: AIService | None = None) -> None:
        self.db = db
        self.conversations = ConversationRepository(db)
        self.messages = MessageRepository(db)
        self.documents = DocumentRepository(db)
        self.tokens = TokenService(db)
        self.prompts = PromptService(db)
        self.ai = ai or AIService()
        self.timeline = TimelineService(db, ai=self.ai)

    def _get_or_create_conversation(
        self, user: User, conversation_id: int | None, first_message: str
    ) -> Conversation:
        if conversation_id is not None:
            conv = self.conversations.get_for_user(conversation_id, user.id)
            if conv is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found",
                )
            return conv
        title = (first_message[:60] + "…") if len(first_message) > 60 else first_message
        conv = Conversation(user_id=user.id, title=title or "New conversation")
        self.conversations.add(conv)
        return conv

    def _build_document_context(self, user: User, document_ids: list[int]) -> str:
        docs = self.documents.get_many_for_user(document_ids, user.id)
        chunks: list[str] = []
        for d in docs:
            if d.extracted_text:
                chunks.append(f"[Document: {d.filename}]\n{d.extracted_text.strip()}")
        if not chunks:
            return ""
        return f"{USER_CONTENT_GUARD}\n\n" + "\n\n".join(chunks)

    def send_message(self, user: User, data: ChatRequest) -> tuple[Conversation, Message]:
        conv = self._get_or_create_conversation(
            user, data.conversation_id, data.message
        )

        history = self.messages.history(conv.id) if conv.id else []
        doc_context = self._build_document_context(user, data.document_ids)
        system_prompt = self.prompts.active_system_prompt() + language_instruction(
            user.language
        )

        # Build the message list for the model (recent history + new turn).
        model_messages: list[dict[str, str]] = []
        for m in history[-_MAX_HISTORY:]:
            if m.role in (MessageRole.user, MessageRole.assistant):
                model_messages.append({"role": m.role.value, "content": m.content})

        user_content = data.message
        if doc_context:
            user_content = f"{doc_context}\n\n---\n\nUser message:\n{data.message}"
        model_messages.append({"role": "user", "content": user_content})

        # Pre-flight token gate based on an estimate of everything we send.
        estimated = estimate_tokens(
            system_prompt + "".join(m["content"] for m in model_messages)
        ) + 512  # headroom for the response
        self.tokens.ensure_within_limit(user, estimated)

        # Persist the user's message before calling the model.
        user_msg = Message(
            conversation_id=conv.id,
            role=MessageRole.user,
            content=data.message,
            token_count=estimate_tokens(data.message),
        )
        self.messages.add(user_msg)

        # Call the model.
        result: AIResult = self.ai.complete(
            system_prompt=system_prompt, messages=model_messages
        )

        assistant_msg = Message(
            conversation_id=conv.id,
            role=MessageRole.assistant,
            content=result.text,
            token_count=result.output_tokens,
        )
        self.messages.add(assistant_msg)

        self.tokens.record(
            user,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            model=result.model,
            conversation_id=conv.id,
        )

        # Best-effort: pull any dated facts out of the user's message into the
        # running case timeline. Never raises — failures are logged and skipped.
        self.timeline.extract_from_text(
            user,
            data.message,
            source_type=TimelineSourceType.message,
            source_id=user_msg.id,
            conversation_id=conv.id,
        )

        self.db.commit()
        self.db.refresh(assistant_msg)
        return conv, assistant_msg
