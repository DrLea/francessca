"""User repository."""
from __future__ import annotations

from sqlalchemy import select

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email.lower()))

    def get_by_google_id(self, google_id: str) -> User | None:
        return self.db.scalar(select(User).where(User.google_id == google_id))

    def all_users(self, limit: int = 200, offset: int = 0) -> list[User]:
        return list(
            self.db.scalars(
                select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
            )
        )
