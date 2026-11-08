"""Orders, lawyer feedback and client reviews.

An *order* is a client sending their prepared case to one lawyer in the
directory. The lawyer sees a contact-free preview plus a quality score and
either accepts or declines; accepting is what uses up one of their orders
(the first few are free) and is what reveals the client's contact details.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.case import JSONType


class OrderStatus(str, enum.Enum):
    pending = "pending"  # sent by the client, waiting for the lawyer
    accepted = "accepted"  # lawyer took it; contact details revealed
    declined = "declined"
    cancelled = "cancelled"  # withdrawn by the client before a response
    closed_won = "closed_won"  # lawyer and client made a deal
    closed_lost = "closed_lost"  # accepted, but nothing came of it


# Statuses that have used up one of the lawyer's orders.
BILLABLE_STATUSES = (
    OrderStatus.accepted.value,
    OrderStatus.closed_won.value,
    OrderStatus.closed_lost.value,
)
CLOSED_STATUSES = (OrderStatus.closed_won.value, OrderStatus.closed_lost.value)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    lawyer_id: Mapped[int] = mapped_column(
        ForeignKey("lawyers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    case_id: Mapped[int | None] = mapped_column(
        ForeignKey("cases.id", ondelete="SET NULL"), nullable=True
    )

    # Plain strings rather than a Postgres ENUM: adding a status later is
    # then a code change, not a migration.
    status: Mapped[str] = mapped_column(
        String(16), default=OrderStatus.pending.value, index=True, nullable=False
    )
    message: Mapped[str | None] = mapped_column(Text)

    # A snapshot of what was sent, so the lawyer keeps seeing exactly that
    # even if the client later regenerates or deletes the case.
    case_title: Mapped[str | None] = mapped_column(String(255))
    case_type: Mapped[str | None] = mapped_column(String(64))
    case_summary: Mapped[dict] = mapped_column(JSONType, default=dict)

    # 0-100, how complete the case was when it was sent. See lead_quality.py.
    quality_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quality_breakdown: Mapped[dict] = mapped_column(JSONType, default=dict)

    # Set when the lawyer accepts: whether it came out of the free allowance.
    is_free: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # What the lawyer says the deal was worth (their own bookkeeping).
    deal_value: Mapped[float | None] = mapped_column(Numeric(12, 2))

    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    client: Mapped["User"] = relationship()
    lawyer: Mapped["Lawyer"] = relationship()
    review: Mapped["LawyerReview | None"] = relationship(
        back_populates="order", uselist=False, cascade="all, delete-orphan"
    )


class FeedbackStatus(str, enum.Enum):
    new = "new"
    reviewed = "reviewed"


FEEDBACK_CATEGORIES = ("lead_quality", "platform", "bug", "idea", "other")


class LawyerFeedback(Base):
    """A quick comment from a lawyer about the leads or the platform."""

    __tablename__ = "lawyer_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lawyer_id: Mapped[int] = mapped_column(
        ForeignKey("lawyers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Optional: the specific order the comment is about.
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    category: Mapped[str] = mapped_column(String(24), default="lead_quality", nullable=False)
    rating: Mapped[int | None] = mapped_column(Integer)  # 1-5, optional
    comment: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(
        String(16), default=FeedbackStatus.new.value, index=True, nullable=False
    )
    admin_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    lawyer: Mapped["Lawyer"] = relationship()
    order: Mapped["Order | None"] = relationship()


class LawyerReview(Base):
    """A client's rating of a lawyer, one per closed order."""

    __tablename__ = "lawyer_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    lawyer_id: Mapped[int] = mapped_column(
        ForeignKey("lawyers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    order: Mapped["Order"] = relationship(back_populates="review")
