"""Lawyer and specialization models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
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

    content_hash: Mapped[str | None] = mapped_column(String(64))  # change detection
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    specializations: Mapped[list["LawyerSpecialization"]] = relationship(
        back_populates="lawyer", cascade="all, delete-orphan"
    )


class LawyerSpecialization(Base):
    __tablename__ = "lawyer_specializations"
    __table_args__ = (UniqueConstraint("lawyer_id", "name", name="uq_lawyer_spec"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lawyer_id: Mapped[int] = mapped_column(
        ForeignKey("lawyers.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)

    lawyer: Mapped["Lawyer"] = relationship(back_populates="specializations")
