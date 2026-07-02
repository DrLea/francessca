"""Current-user profile routes (mounted at /me)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UserOut, UserUpdate

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
