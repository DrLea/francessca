"""Authentication service: registration, login, Google OAuth."""
from __future__ import annotations

import httpx
from fastapi import HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy.orm import Session

from app.config import settings
from app.core.logging import get_logger, log_event
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserTier
from app.repositories.user_repo import UserRepository
from app.schemas.auth import GoogleAuthRequest, LoginRequest, RegisterRequest

log = get_logger("francessca.auth")


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def _default_limit(self) -> int:
        return settings.free_tier_token_limit

    def register(self, data: RegisterRequest) -> User:
        if self.users.get_by_email(data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
            )
        user = User(
            email=data.email.lower(),
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            language=data.language,
            tier=UserTier.free,
            token_limit=self._default_limit(),
        )
        self.users.add(user)
        self.users.commit()
        log_event(log, "auth_register", user_id=user.id, email=user.email)
        return user

    def login(self, data: LoginRequest) -> User:
        user = self.users.get_by_email(data.email)
        if not user or not user.password_hash or not verify_password(
            data.password, user.password_hash
        ):
            log_event(log, "auth_login_failed", email=data.email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        log_event(log, "auth_login", user_id=user.id)
        return user

    def google_login(self, data: GoogleAuthRequest) -> User:
        if not settings.google_client_id:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Google OAuth is not configured",
            )
        try:
            info = google_id_token.verify_oauth2_token(
                data.id_token,
                google_requests.Request(),
                settings.google_client_id,
            )
        except ValueError as exc:  # invalid token
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token",
            ) from exc

        google_id = info["sub"]
        email = info.get("email", "").lower()
        user = self.users.get_by_google_id(google_id) or (
            self.users.get_by_email(email) if email else None
        )
        if user is None:
            user = User(
                email=email,
                google_id=google_id,
                full_name=info.get("name"),
                tier=UserTier.free,
                token_limit=self._default_limit(),
            )
            self.users.add(user)
        elif not user.google_id:
            user.google_id = google_id  # link existing account
        self.users.commit()
        log_event(log, "auth_google", user_id=user.id)
        return user

    @staticmethod
    def issue_token(user: User) -> str:
        return create_access_token(user.id, extra={"role": user.role.value})
