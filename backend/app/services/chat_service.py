"""Chat orchestration: history, token gating, AI call, persistence."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.clarify import (
    CLARIFY_PROTOCOL,
    parse_questions,
    render_questions_for_history,
)
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
from app.schemas.chat import ChatRequest, ClarifyAnswer
from app.services.ai_service import AIResult, AIService, build_ai_service
from app.services.prompt_service import PromptService
from app.services.timeline_service import TimelineService
from app.services.token_service import TokenService, estimate_tokens

# Keep the prompt context bounded: only send the most recent N turns.
_MAX_HISTORY = 20


def compose_user_text(message: str, answers: list[ClarifyAnswer]) -> str:
    """Fold answers to clarifying questions into one readable user turn.

    The whole batch travels as a single message, which is what keeps the
    number of model calls identical to the old free-text flow no matter how
    many questions were asked.
    """
    message = message.strip()
    if not answers:
        return message

    lines: list[str] = []
    for a in answers:
        answer = (a.answer or "").strip()
        lines.append(f"- {a.question.strip()}\n  {answer or '(skipped)'}")
    block = "Answers to your questions:\n" + "\n".join(lines)

    if all(not (a.answer or "").strip() for a in answers):
        block += (
            "\n\n(The user skipped these questions. Continue with what you "
            "already know and do not simply re-ask them.)"
        )
    return f"{message}\n\n{block}".strip() if message else block


class ChatService:
    def __init__(self, db: Session, ai: AIService | None = None) -> None:
        self.db = db
        self.conversations = ConversationRepository(db)
        self.messages = MessageRepository(db)
        self.documents = DocumentRepository(db)
        self.tokens = TokenService(db)
        self.prompts = PromptService(db)
        self.ai = ai or build_ai_service()
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
        # Attached documents share the prompt with the conversation, so no
        # single one may fill it. Half the backend's budget, split between
        # however many are attached.
        budget = getattr(self.ai, "context_char_budget", None)
        per_doc = (budget // 2) // max(1, len(docs)) if budget and docs else None

        chunks: list[str] = []
        for d in docs:
            if not d.extracted_text:
                continue
            text = d.extracted_text.strip()
            if per_doc and len(text) > per_doc:
                text = text[:per_doc] + "\n[... truncated to fit the model's context]"
            chunks.append(f"[Document: {d.filename}]\n{text}")
        if not chunks:
            return ""
        return f"{USER_CONTENT_GUARD}\n\n" + "\n\n".join(chunks)

    @staticmethod
    def _history_content(m: Message) -> str:
        """Replay an assistant turn including the questions it asked.

        Questions live in their own column rather than in `content`, so
        without this the model would see its own previous turn as if it had
        asked nothing and would happily ask again.
        """
        if m.role is not MessageRole.assistant or not m.questions:
            return m.content
        rendered = render_questions_for_history(m.questions)
        return f"{m.content}\n\n{rendered}".strip() if rendered else m.content

    def send_message(
        self, user: User, data: ChatRequest
    ) -> tuple[Conversation, Message, Message]:
        """Handle one user turn. Returns (conversation, user msg, reply)."""
        user_text = compose_user_text(data.message, data.answers)
        conv = self._get_or_create_conversation(user, data.conversation_id, user_text)

        history = self.messages.history(conv.id) if conv.id else []
        doc_context = self._build_document_context(user, data.document_ids)
        system_prompt = (
            self.prompts.active_system_prompt()
            + language_instruction(user.language)
            + CLARIFY_PROTOCOL
        )

        # Build the message list for the model (recent history + new turn).
        model_messages: list[dict[str, str]] = []
        for m in history[-_MAX_HISTORY:]:
            if m.role in (MessageRole.user, MessageRole.assistant):
                content = self._history_content(m)
                if content.strip():
                    model_messages.append({"role": m.role.value, "content": content})

        user_content = user_text
        if doc_context:
            user_content = f"{doc_context}\n\n---\n\nUser message:\n{user_text}"
        model_messages.append({"role": "user", "content": user_content})

        # Keep the whole prompt inside what this backend can actually hold,
        # dropping the oldest turns first. The newest turn always survives:
        # without it there is nothing to answer.
        budget = getattr(self.ai, "context_char_budget", None)
        if budget:
            overhead = len(system_prompt)
            while len(model_messages) > 1 and (
                overhead + sum(len(m["content"]) for m in model_messages) > budget
            ):
                model_messages.pop(0)

        # Pre-flight token gate based on an estimate of everything we send.
        estimated = estimate_tokens(
            system_prompt + "".join(m["content"] for m in model_messages)
        ) + 512  # headroom for the response
        self.tokens.ensure_within_limit(user, estimated)

        # Persist the user's message before calling the model.
        user_msg = Message(
            conversation_id=conv.id,
            role=MessageRole.user,
            content=user_text,
            token_count=estimate_tokens(user_text),
        )
        self.messages.add(user_msg)

        # Call the model. One call per turn, however many questions came back.
        # Generous max_tokens: the question block is the LAST thing in the
        # reply, so a truncated response loses the questions entirely.
        result: AIResult = self.ai.complete(
            system_prompt=system_prompt, messages=model_messages, max_tokens=2000
        )

        # Split the reply into what the user sees and what the UI turns into
        # a one-question-at-a-time flow.
        text, questions = parse_questions(result.text)

        assistant_msg = Message(
            conversation_id=conv.id,
            role=MessageRole.assistant,
            content=text,
            token_count=result.output_tokens,
            questions=questions or None,
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
        # The previous assistant turn goes along as context, so "add it to my
        # timeline" can resolve to the appointment discussed a moment ago.
        previous = next(
            (
                m.content
                for m in reversed(history)
                if m.role is MessageRole.assistant and m.content.strip()
            ),
            None,
        )
        self.timeline.extract_from_text(
            user,
            user_text,
            source_type=TimelineSourceType.message,
            source_id=user_msg.id,
            conversation_id=conv.id,
            context=previous,
        )

        self.db.commit()
        self.db.refresh(assistant_msg)
        self.db.refresh(user_msg)
        return conv, user_msg, assistant_msg
