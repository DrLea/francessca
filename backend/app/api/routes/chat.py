"""Chat routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.repositories.conversation_repo import ConversationRepository, MessageRepository
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationOut,
    MessageOut,
)
from app.services.chat_service import ChatService
from app.services.token_service import TokenService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def send_message(
    data: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    service = ChatService(db)
    conv, assistant_msg = service.send_message(user, data)
    db.refresh(user)
    remaining = TokenService(db).remaining(user)
    return ChatResponse(
        conversation_id=conv.id,
        message=MessageOut.model_validate(assistant_msg),
        tokens_used=user.tokens_used,
        tokens_remaining=remaining,
    )


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ConversationOut]:
    convs = ConversationRepository(db).list_for_user(user.id)
    return [ConversationOut.model_validate(c) for c in convs]


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationDetail:
    conv = ConversationRepository(db).get_for_user(conversation_id, user.id)
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    messages = MessageRepository(db).history(conv.id)
    detail = ConversationDetail.model_validate(conv)
    detail.messages = [MessageOut.model_validate(m) for m in messages]
    return detail
