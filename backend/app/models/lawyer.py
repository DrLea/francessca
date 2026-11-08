"""Lawyer and specialization models."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import (
    Boolean,
    Date,
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

    # --- Subscription ----------------------------------------------------
    # Law firms pay a flat monthly fee, never per client (German law forbids
    # paying for referred mandates, §49b Abs. 3 BRAO). The first months are
    # a free trial that starts when the profile is approved; after that an
    # admin records payment by moving paid_until forward. No payment
    # provider is wired in yet.
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_until: Mapped[date | None] = mapped_column(Date)

    # --- Verification ----------------------------------------------------
    # 1. Official register: checked by an admin in the BRAK
    #    Bundesrechtsanwaltsregister (name, chamber, admission).
    brak_register_id: Mapped[str | None] = mapped_column(String(64))
    chamber: Mapped[str | None] = mapped_column(String(128))
    admission_date: Mapped[date | None] = mapped_column(Date)
    brak_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # 2. beA code: a one-time code sent to the lawyer's official beA mailbox
    #    (only admitted lawyers have one); the lawyer types it back in.
    bea_code_hash: Mapped[str | None] = mapped_column(String(128))
    bea_code_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    bea_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # 3. ID check: video ident matching the person to the registered name.
    #    not_started | pending | passed | failed. The provider integration is
    #    not wired in yet; an admin records the result.
    id_check_status: Mapped[str] = mapped_column(
        String(16), default="not_started", server_default="not_started", nullable=False
    )
    id_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # 4. Re-check: verification is valid for a year, then repeated.
    verified_until: Mapped[date | None] = mapped_column(Date)
    # User reports can get a lawyer suspended at once; a suspended lawyer
    # disappears from the directory and cannot receive cases.
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    suspension_reason: Mapped[str | None] = mapped_column(Text)

    # Law Clinic / university partner this profile belongs to, if any.
    partner_id: Mapped[int | None] = mapped_column(
        ForeignKey("partners.id", ondelete="SET NULL"), nullable=True, index=True
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

    partner: Mapped["Partner | None"] = relationship()

    # --- Derived state -------------------------------------------------------
    @property
    def is_suspended(self) -> bool:
        return self.suspended_at is not None

    @property
    def is_verified(self) -> bool:
        """All checks passed and the yearly re-check is not overdue."""
        return (
            self.brak_checked_at is not None
            and self.bea_verified_at is not None
            and self.id_check_status == "passed"
            and self.verified_until is not None
            and self.verified_until >= date.today()
            and not self.is_suspended
        )

    def subscription_state(self, now: datetime | None = None) -> str:
        """not_started | trial | active | expired."""
        now = now or datetime.now(timezone.utc)
        if self.paid_until is not None and self.paid_until >= now.date():
            return "active"
        if self.trial_ends_at is not None:
            ends = self.trial_ends_at
            if ends.tzinfo is None:  # SQLite hands back naive datetimes
                ends = ends.replace(tzinfo=timezone.utc)
            return "trial" if ends > now else "expired"
        return "not_started" if self.paid_until is None else "expired"

    def start_trial(self, months: int) -> None:
        if self.trial_ends_at is None:
            self.trial_ends_at = datetime.now(timezone.utc) + timedelta(days=30 * months)

    specializations: Mapped[list["LawyerSpecialization"]] = relationship(
        back_populates="lawyer", cascade="all, delete-orphan"
    )

    @property
    def accepts_requests(self) -> bool:
        """Only an approved, not suspended lawyer with an account can receive
        a case through the app."""
        return self.user_id is not None and self.is_published and not self.is_suspended


class LawyerSpecialization(Base):
    __tablename__ = "lawyer_specializations"
    __table_args__ = (UniqueConstraint("lawyer_id", "name", name="uq_lawyer_spec"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lawyer_id: Mapped[int] = mapped_column(
        ForeignKey("lawyers.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)

    lawyer: Mapped["Lawyer"] = relationship(back_populates="specializations")
