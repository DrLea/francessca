"""Lawyer and specialization models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Lawyer(Base):
    __tablename__ = "lawyers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Stable hash of the source profile, used for upsert/caching during sync.
    source_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    law_firm: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(128), index=True)
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(64))
    website: Mapped[str | None] = mapped_column(String(512))
    address: Mapped[str | None] = mapped_column(Text)
    photo_url: Mapped[str | None] = mapped_column(String(512))
    profile_url: Mapped[str | None] = mapped_column(String(512))
    languages: Mapped[str | None] = mapped_column(String(255))  # comma-separated

    # --- Lawyers who registered an account (the lawyer portal) ---------
    # NULL for directory rows that came from the scraper or the seed data.
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True
    )
    # A self-registered lawyer stays out of the directory until an admin
    # approves them. Scraped rows are published from the start.
    is_published: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False, index=True
    )
    bio: Mapped[str | None] = mapped_column(Text)
    years_experience: Mapped[int | None] = mapped_column(Integer)
    consultation_fee: Mapped[str | None] = mapped_column(String(128))
    office_hours: Mapped[str | None] = mapped_column(String(255))
    # Orders an admin has unlocked on top of the free allowance.
    extra_orders: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    # Denormalised from lawyer_reviews so the directory can show and sort
    # by rating without a join.
    rating_avg: Mapped[float | None] = mapped_column(Float)
    rating_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )

    content_hash: Mapped[str | None] = mapped_column(String(64))  # change detection
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    specializations: Mapped[list["LawyerSpecialization"]] = relationship(
        back_populates="lawyer", cascade="all, delete-orphan"
    )

    @property
    def accepts_requests(self) -> bool:
        """Only a lawyer with an account can receive a case through the app."""
        return self.user_id is not None and self.is_published


class LawyerSpecialization(Base):
    __tablename__ = "lawyer_specializations"
    __table_args__ = (UniqueConstraint("lawyer_id", "name", name="uq_lawyer_spec"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lawyer_id: Mapped[int] = mapped_column(
        ForeignKey("lawyers.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)

    lawyer: Mapped["Lawyer"] = relationship(back_populates="specializations")
