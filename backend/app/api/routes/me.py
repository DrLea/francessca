"""Current-user profile routes (mounted at /me)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, UserTier
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


class PlanChange(BaseModel):
    tier: UserTier


@router.post("/plan", response_model=UserOut)
def change_plan(
    data: PlanChange,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Switch plan. Free while Francessca is in beta — there is no payment
    step yet, so this only moves the tier and the matching token allowance.
    Wire a payment provider in front of this before charging anyone.
    """
    user.tier = data.tier
    user.token_limit = (
        None if data.tier is UserTier.premium else settings.free_tier_token_limit
    )
    db.commit()
    db.refresh(user)
    return user
