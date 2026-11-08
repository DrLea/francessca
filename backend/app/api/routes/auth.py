"""Auth routes."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    GoogleAuthRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.portal import LawyerRegisterRequest
from app.schemas.user import UserOut
from app.services import email_service
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    service = AuthService(db)
    user = service.register(data)
    return TokenResponse(access_token=service.issue_token(user))


@router.post(
    "/register-lawyer", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
def register_lawyer(
    data: LawyerRegisterRequest,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Sign up as a lawyer. Signed in straight away; listed in the
    directory once an admin has approved the profile."""
    service = AuthService(db)
    user = service.register_lawyer(data)
    background.add_task(
        email_service.lawyer_registered_admin, data.name, user.email, data.city
    )
    return TokenResponse(access_token=service.issue_token(user))


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    service = AuthService(db)
    user = service.login(data)
    return TokenResponse(access_token=service.issue_token(user))


@router.post("/google", response_model=TokenResponse)
def google(data: GoogleAuthRequest, db: Session = Depends(get_db)) -> TokenResponse:
    service = AuthService(db)
    user = service.google_login(data)
    return TokenResponse(access_token=service.issue_token(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
