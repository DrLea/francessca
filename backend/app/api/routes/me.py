"""Current-user profile routes (mounted at /me)."""
from __future__ import annotations

import json
import os
import shutil
import zipfile
from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.crypto import read_decrypted
from app.core.logging import get_logger, log_event
from app.database import get_db
from app.dependencies import get_current_user
from app.models.case import Case
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.export import Export
from app.models.message import Message
from app.models.order import Order
from app.models.timeline_event import TimelineEvent
from app.models.user import User, UserRole
from app.schemas.common import MessageResponse
from app.schemas.user import UserOut, UserUpdate

log = get_logger("francessca.privacy")

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("", response_model=UserOut)
def update_me(
    data: UserUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.language is not None:
        user.language = data.language
    db.commit()
    db.refresh(user)
    return user


# --- Privacy: consent, export, delete -------------------------------------
@router.post("/consent", response_model=UserOut)
def give_data_consent(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> User:
    """Agree to keep case data on Francesca's servers in Germany."""
    if user.data_consent_at is None:
        user.data_consent_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)
    return user


def _user_files(db: Session, user: User) -> tuple[list[Document], list[Export]]:
    documents = list(db.scalars(select(Document).where(Document.user_id == user.id)))
    exports = list(
        db.scalars(select(Export).join(Case, Export.case_id == Case.id).where(Case.user_id == user.id))
    )
    return documents, exports


@router.get("/export")
def export_my_data(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    """Everything Francesca holds about this account, in one ZIP (GDPR
    Art. 15/20): profile, conversations, timeline, cases, requests sent to
    lawyers, and the original uploaded files (decrypted)."""
    conversations = list(
        db.scalars(select(Conversation).where(Conversation.user_id == user.id))
    )
    data = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "profile": {
            "email": user.email,
            "full_name": user.full_name,
            "language": user.language,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "data_consent_at": user.data_consent_at.isoformat() if user.data_consent_at else None,
        },
        "conversations": [
            {
                "id": c.id,
                "title": c.title,
                "messages": [
                    {"role": m.role.value if hasattr(m.role, "value") else m.role,
                     "content": m.content,
                     "created_at": m.created_at.isoformat() if m.created_at else None}
                    for m in db.scalars(
                        select(Message).where(Message.conversation_id == c.id).order_by(Message.id)
                    )
                ],
            }
            for c in conversations
        ],
        "timeline": [
            {"date": e.event_date.isoformat() if e.event_date else None,
             "description": e.description, "is_deadline": e.is_deadline}
            for e in db.scalars(select(TimelineEvent).where(TimelineEvent.user_id == user.id))
        ],
        "cases": [
            {"id": c.id, "title": c.title, "summary": c.summary}
            for c in db.scalars(select(Case).where(Case.user_id == user.id))
        ],
        "requests_to_lawyers": [
            {"lawyer_id": o.lawyer_id, "status": o.status, "case_title": o.case_title,
             "consent_at": o.consent_at.isoformat() if o.consent_at else None,
             "consent_withdrawn_at": o.consent_withdrawn_at.isoformat() if o.consent_withdrawn_at else None}
            for o in db.scalars(select(Order).where(Order.client_id == user.id))
        ],
    }
    documents, _ = _user_files(db, user)
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("francesca_data.json", json.dumps(data, ensure_ascii=False, indent=2, default=str))
        for i, doc in enumerate(documents, start=1):
            if os.path.exists(doc.stored_path):
                zf.writestr(f"documents/{i:02d}_{doc.filename}", read_decrypted(doc.stored_path))
    log_event(log, "data_export", user_id=user.id)
    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="francesca-my-data.zip"'},
    )


@router.delete("", response_model=MessageResponse)
def delete_my_account(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> MessageResponse:
    """Delete the account and everything in it, files on disk included.
    Lawyers keep nothing they were sent: orders cascade with the client."""
    if user.role == UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Admin accounts cannot delete themselves"
        )
    documents, exports = _user_files(db, user)
    paths = [d.stored_path for d in documents] + [e.stored_path for e in exports]
    user_id = user.id
    if user.role == UserRole.lawyer:
        from app.models.lawyer import Lawyer

        for lawyer in db.scalars(select(Lawyer).where(Lawyer.user_id == user.id)):
            lawyer.is_published = False  # no account behind it any more
    db.delete(user)
    db.commit()
    for path in paths:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except OSError:
            log.warning("could not remove %s", path)
    shutil.rmtree(os.path.join(settings.upload_dir, str(user_id)), ignore_errors=True)
    log_event(log, "account_deleted", user_id=user_id)
    return MessageResponse(detail="Your account and all its data were deleted.")
