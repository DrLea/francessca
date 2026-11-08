"""Trust and partnership models: user reports about lawyers, and partner
organisations (universities, Law Clinics, NGOs) holding a partner licence."""
from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ReportStatus(str, enum.Enum):
    open = "open"
    resolved = "resolved"  # acted on (e.g. lawyer suspended)
    dismissed = "dismissed"


REPORT_REASONS = ("not_a_lawyer", "misconduct", "no_response", "privacy", "other")


class LawyerReport(Base):
    """A client reporting a lawyer. Enough distinct open reports suspend the
    lawyer automatically until an admin has looked at them."""

    __tablename__ = "lawyer_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lawyer_id: Mapped[int] = mapped_column(
        ForeignKey("lawyers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    reporter_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str] = mapped_column(String(24), nullable=False)
    details: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(16), default=ReportStatus.open.value, index=True, nullable=False
    )
    admin_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    lawyer: Mapped["Lawyer"] = relationship()


PARTNER_KINDS = ("university", "law_clinic", "international_office", "ngo", "integration_office")


class Partner(Base):
    """A university, Law Clinic or NGO with a partner licence (EUR 500/month).

    Members (e.g. supervised law students of a Law Clinic) get lawyer-portal
    accounts linked to the partner and help people for free.
    """

    __tablename__ = "partners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), default="university", nullable=False)
    city: Mapped[str | None] = mapped_column(String(128))
    contact_name: Mapped[str | None] = mapped_column(String(255))
    contact_email: Mapped[str | None] = mapped_column(String(320))
    monthly_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=500, nullable=False)
    # trial | active | inactive -- managed by an admin, no payment provider.
    status: Mapped[str] = mapped_column(String(16), default="trial", nullable=False)
    paid_until: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
