"""Dashboard & usage routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.case import Case
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.export import Export
from app.models.timeline_event import TimelineEvent
from app.models.user import User
from app.schemas.common import DashboardOut, UsageOut
from app.services.token_service import TokenService

router = APIRouter(tags=["dashboard"])


def _count(db: Session, model, **filters) -> int:
    stmt = select(func.count()).select_from(model)
    for attr, value in filters.items():
        stmt = stmt.where(getattr(model, attr) == value)
    return db.scalar(stmt) or 0


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> DashboardOut:
    conv_count = _count(db, Conversation, user_id=user.id)
    doc_count = _count(db, Document, user_id=user.id)
    case_count = _count(db, Case, user_id=user.id)
    export_count = db.scalar(
        select(func.count())
        .select_from(Export)
        .join(Case, Export.case_id == Case.id)
        .where(Case.user_id == user.id)
    ) or 0
    timeline_count = _count(db, TimelineEvent, user_id=user.id)
    return DashboardOut(
        conversations=conv_count,
        documents=doc_count,
        cases=case_count,
        exports=export_count,
        timeline_events=timeline_count,
        tokens_used=user.tokens_used,
        token_limit=user.token_limit,
    )


@router.get("/usage", response_model=UsageOut)
def usage(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> UsageOut:
    remaining = TokenService(db).remaining(user)
    return UsageOut(
        token_limit=user.token_limit,
        tokens_used=user.tokens_used,
        tokens_remaining=remaining,
        tier=user.tier.value,
    )
