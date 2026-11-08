"""Lawyer verification: register check, beA code, ID check, yearly re-check,
user reports and instant suspension.

How each check works today:

* **Register** -- the lawyer enters their BRAK register entry, chamber and
  admission date; an admin looks them up in the official
  Bundesrechtsanwaltsregister (https://www.rechtsanwaltsregister.org) and
  ticks "register checked". There is no public API to automate this.
* **beA code** -- an admin generates a one-time code here and sends it to
  the lawyer's official beA mailbox (only admitted lawyers have one). The
  lawyer types it back into the portal. Only a hash is stored.
* **ID check** -- video ident. No provider is integrated yet; an admin
  records the result (pending / passed / failed).
* **Re-check** -- when all three pass, the profile is verified for a year
  (``verified_until``); after that the badge disappears until re-checked.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.logging import get_logger, log_event
from app.models.lawyer import Lawyer
from app.models.trust import LawyerReport, ReportStatus

log = get_logger("francessca.verification")

BEA_CODE_TTL = timedelta(days=30)
# No 0/O/1/I: the code is typed by hand from a beA message.
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _hash_code(code: str) -> str:
    normalised = code.strip().upper().replace("-", "").replace(" ", "")
    return hmac.new(
        settings.jwt_secret.encode(), normalised.encode(), hashlib.sha256
    ).hexdigest()


class VerificationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # --- beA -----------------------------------------------------------------
    def issue_bea_code(self, lawyer: Lawyer) -> str:
        """New one-time code. Returned once, for the admin to send by beA."""
        raw = "".join(secrets.choice(_ALPHABET) for _ in range(8))
        lawyer.bea_code_hash = _hash_code(raw)
        lawyer.bea_code_sent_at = _now()
        lawyer.bea_verified_at = None
        log_event(log, "bea_code_issued", lawyer_id=lawyer.id)
        return f"{raw[:4]}-{raw[4:]}"

    def confirm_bea_code(self, lawyer: Lawyer, code: str) -> None:
        sent = _aware(lawyer.bea_code_sent_at)
        if not lawyer.bea_code_hash or sent is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "No beA code has been sent yet")
        if _now() - sent > BEA_CODE_TTL:
            raise HTTPException(status.HTTP_410_GONE, "This code has expired; ask for a new one")
        if not hmac.compare_digest(lawyer.bea_code_hash, _hash_code(code)):
            log_event(log, "bea_code_mismatch", lawyer_id=lawyer.id)
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "The code does not match")
        lawyer.bea_verified_at = _now()
        lawyer.bea_code_hash = None
        self.refresh(lawyer)
        log_event(log, "bea_verified", lawyer_id=lawyer.id)

    # --- Yearly re-check -------------------------------------------------------
    @staticmethod
    def refresh(lawyer: Lawyer) -> None:
        """Start a new verification year once every check has passed."""
        all_passed = (
            lawyer.brak_checked_at is not None
            and lawyer.bea_verified_at is not None
            and lawyer.id_check_status == "passed"
        )
        if not all_passed:
            lawyer.verified_until = None
        elif lawyer.verified_until is None or lawyer.verified_until < date.today():
            lawyer.verified_until = date.today() + timedelta(days=365)

    @staticmethod
    def start_recheck(lawyer: Lawyer) -> None:
        """Yearly re-check: clear the checks so they are done again."""
        lawyer.brak_checked_at = None
        lawyer.bea_verified_at = None
        lawyer.id_check_status = "pending"
        lawyer.verified_until = None

    # --- Suspension ------------------------------------------------------------
    @staticmethod
    def suspend(lawyer: Lawyer, reason: str) -> None:
        if lawyer.suspended_at is None:
            lawyer.suspended_at = _now()
        lawyer.suspension_reason = reason
        log_event(log, "lawyer_suspended", lawyer_id=lawyer.id)

    @staticmethod
    def lift(lawyer: Lawyer) -> None:
        lawyer.suspended_at = None
        lawyer.suspension_reason = None
        log_event(log, "lawyer_unsuspended", lawyer_id=lawyer.id)

    def open_report_count(self, lawyer_id: int) -> int:
        return (
            self.db.scalar(
                select(func.count(func.distinct(LawyerReport.reporter_id))).where(
                    LawyerReport.lawyer_id == lawyer_id,
                    LawyerReport.status == ReportStatus.open.value,
                )
            )
            or 0
        )

    def after_report(self, lawyer: Lawyer) -> bool:
        """Suspend at once when enough different people report the lawyer.
        Returns True if this report triggered the suspension."""
        threshold = max(1, settings.report_suspend_threshold)
        if lawyer.suspended_at is None and self.open_report_count(lawyer.id) >= threshold:
            self.suspend(lawyer, f"Automatic: {threshold} open user reports")
            return True
        return False
