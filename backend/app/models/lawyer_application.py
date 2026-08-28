"""Lawyer sign-up applications.

A lawyer applies from the public landing page; nothing they submit appears
in the directory until an admin approves it, at which point the application
is turned into a real `Lawyer` row.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column


from app.database import Base


class ApplicationStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class LawyerApplication(Base):
    __tablename__ = "lawyer_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    law_firm: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(128))
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(64))
    website: Mapped[str | None] = mapped_column(String(512))
    address: Mapped[str | None] = mapped_column(Text)
    # Comma-separated, same shape as the directory rows they become.
    languages: Mapped[str | None] = mapped_column(String(255))
    specializations: Mapped[str | None] = mapped_column(String(512))
    message: Mapped[str | None] = mapped_column(Text)

    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="lawyer_application_status"),
        default=ApplicationStatus.pending,
        nullable=False,
        index=True,
    )
    # The directory entry created on approval, if any.
    lawyer_id: Mapped[int | None] = mapped_column(
        ForeignKey("lawyers.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
