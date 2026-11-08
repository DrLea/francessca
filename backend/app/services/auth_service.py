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
from app.models.user import User, UserRole, UserTier
from app.repositories.user_repo import UserRepository
from app.schemas.auth import GoogleAuthRequest, LoginRequest, RegisterRequest
from app.schemas.portal import LawyerRegisterRequest

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

    def register_lawyer(self, data: LawyerRegisterRequest) -> User:
        """Create a lawyer account in one step.

        The account works immediately (the lawyer can sign in and complete
        their profile), but the directory entry is created unpublished and
        the application waits for an admin, exactly like the older
        contact-form applications.
        """
        from app.models.lawyer import Lawyer, LawyerSpecialization
        from app.models.lawyer_application import LawyerApplication

        if self.users.get_by_email(data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
            )
        email = data.email.lower()
        name = data.name.strip()
        user = User(
            email=email,
            password_hash=hash_password(data.password),
            full_name=name,
            language=data.language,
            role=UserRole.lawyer,
            tier=UserTier.free,
            token_limit=self._default_limit(),
        )
        self.users.add(user)  # flushes, so user.id is available

        languages = ", ".join(data.languages) or None
        # De-duplicate case-insensitively: (lawyer_id, name) is unique.
        specs: dict[str, str] = {}
        for spec in data.specializations:
            specs.setdefault(spec.lower(), spec)
        lawyer = Lawyer(
            # A source_key of its own, so a scraper sync never touches it.
            source_key=f"account:{user.id}",
            user_id=user.id,
            is_published=False,
            name=name,
            email=email,
            law_firm=data.law_firm,
            city=data.city,
            phone=data.phone,
            languages=languages,
        )
        lawyer.specializations = [LawyerSpecialization(name=n) for n in specs.values()]
        self.db.add(lawyer)
        self.db.flush()
        self.db.add(
            LawyerApplication(
                name=name,
                email=email,
                law_firm=data.law_firm,
                city=data.city,
                phone=data.phone,
                languages=languages,
                specializations=", ".join(specs.values()) or None,
                lawyer_id=lawyer.id,
                user_id=user.id,
            )
        )
        self.users.commit()
        log_event(log, "auth_register_lawyer", user_id=user.id, lawyer_id=lawyer.id)
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
