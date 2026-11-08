"""Shared FastAPI dependencies: current user, admin guard."""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import User, UserRole
from app.repositories.user_repo import UserRepository

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    payload = decode_access_token(creds.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    user = UserRepository(db).get(int(payload["sub"]))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    return user


def require_lawyer(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> "Lawyer":
    """The signed-in user's own lawyer record (the lawyer portal).

    Returned whether or not the profile has been approved yet — a pending
    lawyer can already sign in and complete their profile; the routes that
    need an approved one check `is_published` themselves.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.models.lawyer import Lawyer

    if user.role != UserRole.lawyer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Lawyer account required"
        )
    lawyer = db.scalar(
        select(Lawyer)
        .options(selectinload(Lawyer.specializations))
        .where(Lawyer.user_id == user.id)
    )
    if lawyer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lawyer profile not found"
        )
    return lawyer
