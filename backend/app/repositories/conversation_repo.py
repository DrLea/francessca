"""Conversation & message repositories."""
from __future__ import annotations

from sqlalchemy import select

from app.models.conversation import Conversation
from app.models.message import Message
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    model = Conversation

    def list_for_user(self, user_id: int) -> list[Conversation]:
        return list(
            self.db.scalars(
                select(Conversation)
                .where(Conversation.user_id == user_id)
                .order_by(Conversation.created_at.desc())
            )
        )

    def get_for_user(self, conversation_id: int, user_id: int) -> Conversation | None:
        return self.db.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id, Conversation.user_id == user_id
            )
        )


class MessageRepository(BaseRepository[Message]):
    model = Message

    def history(self, conversation_id: int) -> list[Message]:
        return list(
            self.db.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at)
            )
        )
