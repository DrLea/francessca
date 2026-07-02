"""Admin panel routes. All endpoints require an admin user."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models.conversation import Conversation
from app.models.prompt_version import PromptVersion
from app.models.token_usage import TokenUsage
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.user import AdminUserUpdate, UserOut
from app.seeds.lawyers import sample_lawyers
from app.services.lawyer_service import LawyerService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
def list_users(
    _: User = Depends(require_admin), db: Session = Depends(get_db)
) -> list[UserOut]:
    return [UserOut.model_validate(u) for u in UserRepository(db).all_users()]


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    data: AdminUserUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserOut:
    user = UserRepository(db).get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    for field_name, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field_name, value)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.delete(conv)
    db.commit()
    return {"detail": "deleted"}


@router.post("/lawyers/sync")
def sync_lawyers(
    live: bool = False,
    max_pages: int = 5,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Trigger lawyer synchronisation.

    `live=false` (default) reseeds from the sample dataset; `live=true` runs
    the rak-muenchen scraper (which itself caches and skips unchanged pages).
    """
    service = LawyerService(db)
    if live:
        return service.sync_live(max_pages=max_pages)
    return service.sync_from_parsed(sample_lawyers())


@router.get("/usage")
def ai_usage(
    _: User = Depends(require_admin), db: Session = Depends(get_db)
) -> dict:
    total_in = db.scalar(select(func.coalesce(func.sum(TokenUsage.input_tokens), 0)))
    total_out = db.scalar(select(func.coalesce(func.sum(TokenUsage.output_tokens), 0)))
    requests = db.scalar(select(func.count()).select_from(TokenUsage))
    return {
        "requests": requests,
        "input_tokens": int(total_in or 0),
        "output_tokens": int(total_out or 0),
        "total_tokens": int((total_in or 0) + (total_out or 0)),
    }


# --- Prompt management ---------------------------------------------------
class PromptIn(BaseModel):
    name: str = "francessca-system"
    content: str
    activate: bool = True


@router.get("/prompts")
def list_prompts(
    _: User = Depends(require_admin), db: Session = Depends(get_db)
) -> list[dict]:
    rows = db.scalars(
        select(PromptVersion).order_by(desc(PromptVersion.created_at))
    )
    return [
        {
            "id": p.id,
            "name": p.name,
            "is_active": p.is_active,
            "content": p.content,
            "created_at": p.created_at.isoformat(),
        }
        for p in rows
    ]


@router.post("/prompts", status_code=status.HTTP_201_CREATED)
def create_prompt(
    data: PromptIn,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    prompt = PromptVersion(name=data.name, content=data.content, is_active=data.activate)
    if data.activate:
        # Deactivate any currently-active prompt of the same name.
        for existing in db.scalars(
            select(PromptVersion).where(
                PromptVersion.is_active.is_(True), PromptVersion.name == data.name
            )
        ):
            existing.is_active = False
    db.add(prompt)
    db.commit()
    db.refresh(prompt)
    return {"id": prompt.id, "is_active": prompt.is_active}
