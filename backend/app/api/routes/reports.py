"""Clients reporting a lawyer. Enough distinct reports suspend the lawyer at
once (REPORT_SUSPEND_THRESHOLD); an admin then reviews them."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.logging import get_logger, log_event
from app.database import get_db
from app.dependencies import get_current_user
from app.models.lawyer import Lawyer
from app.models.order import Order
from app.models.trust import LawyerReport, ReportStatus
from app.models.user import User
from app.schemas.portal import ReportCreate, ReportOut
from app.services import email_service
from app.services.verification_service import VerificationService

router = APIRouter(prefix="/reports", tags=["reports"])
log = get_logger("francessca.reports")


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def report_lawyer(
    data: ReportCreate,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LawyerReport:
    lawyer = db.get(Lawyer, data.lawyer_id)
    if lawyer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lawyer not found")
    if data.order_id is not None:
        order = db.get(Order, data.order_id)
        if order is None or order.client_id != user.id or order.lawyer_id != lawyer.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    existing = db.scalar(
        select(LawyerReport).where(
            LawyerReport.lawyer_id == lawyer.id,
            LawyerReport.reporter_id == user.id,
            LawyerReport.status == ReportStatus.open.value,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an open report about this lawyer",
        )
    report = LawyerReport(
        lawyer_id=lawyer.id,
        reporter_id=user.id,
        order_id=data.order_id,
        reason=data.reason,
        details=(data.details or "").strip() or None,
    )
    db.add(report)
    db.flush()
    suspended = VerificationService(db).after_report(lawyer)
    db.commit()
    db.refresh(report)
    log_event(log, "lawyer_reported", lawyer_id=lawyer.id, reason=data.reason, suspended=suspended)
    if settings.contact_email:
        background.add_task(
            email_service.lawyer_reported_admin,
            settings.contact_email, lawyer.name, data.reason, suspended,
        )
    return report


@router.get("", response_model=list[ReportOut])
def my_reports(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[LawyerReport]:
    return list(
        db.scalars(
            select(LawyerReport)
            .where(LawyerReport.reporter_id == user.id)
            .order_by(LawyerReport.created_at.desc())
        )
    )
