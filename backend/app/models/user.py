"""User model."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    user = "user"  # a client preparing a case
    lawyer = "lawyer"  # a lawyer with access to the lawyer portal
    admin = "admin"


class UserTier(str, enum.Enum):
    # Francesca is free for people: there is nothing to buy. "premium" only
    # lifts the hidden fair-use cap and is set by an admin (staff, partner
    # pilots). The enum keeps its old name so no DB migration is needed.
    free = "free"
    premium = "premium"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), default=UserRole.user, nullable=False
    )
    tier: Mapped[UserTier] = mapped_column(
        Enum(UserTier, name="user_tier"), default=UserTier.free, nullable=False
    )

    # Per-user override of the daily fair-use cap; NULL = the default
    # (FAIR_USE_DAILY_TOKENS). tokens_used is a lifetime total for stats.
    token_limit: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    tokens_used: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # Explicit consent to keep this account's case data on Francesca's
    # servers in Germany (GDPR Art. 6(1)(a), 9(2)(a)). Without it the
    # offline app is the way to use Francesca.
    data_consent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    cases: Mapped[list["Case"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    timeline_events: Mapped[list["TimelineEvent"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def is_unlimited(self) -> bool:
        return self.tier == UserTier.premium
