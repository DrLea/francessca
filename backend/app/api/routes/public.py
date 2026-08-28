"""Unauthenticated routes used by the public landing page.

Everything here is readable by anyone, so the lawyer preview deliberately
omits contact details (those stay behind the login on /lawyers) and the
application endpoint only ever creates a *pending* record.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_event
from app.database import get_db
from app.models.lawyer import Lawyer
from app.models.lawyer_application import LawyerApplication
from app.schemas.lawyer_application import (
    LawyerApplicationCreate,
    LawyerApplicationOut,
    LawyerPublicOut,
)

router = APIRouter(prefix="/public", tags=["public"])
log = get_logger("francessca.public")


@router.get("/lawyers")
def preview_lawyers(
    limit: int = Query(6, ge=1, le=24), db: Session = Depends(get_db)
) -> dict:
    """A short, contact-free preview of the directory for the landing page."""
    from sqlalchemy.orm import selectinload

    total = db.scalar(select(func.count()).select_from(Lawyer)) or 0
    rows = db.scalars(
        select(Lawyer)
        .options(selectinload(Lawyer.specializations))
        .order_by(Lawyer.name)
        .limit(limit)
    )
    return {
        "total": total,
        "items": [LawyerPublicOut.model_validate(r).model_dump() for r in rows],
    }


@router.post(
    "/lawyer-applications",
    response_model=LawyerApplicationOut,
    status_code=status.HTTP_201_CREATED,
)
def apply_as_lawyer(
    data: LawyerApplicationCreate, db: Session = Depends(get_db)
) -> LawyerApplicationOut:
    """A lawyer asks to be listed. Stored as pending; an admin reviews it
    before anything reaches the directory."""
    application = LawyerApplication(
        name=data.name.strip(),
        email=str(data.email).lower(),
        law_firm=data.law_firm,
        city=data.city,
        phone=data.phone,
        website=data.website,
        address=data.address,
        languages=", ".join(data.languages) or None,
        specializations=", ".join(data.specializations) or None,
        message=data.message,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    log_event(log, "lawyer_application", id=application.id, email=application.email)
    return LawyerApplicationOut.model_validate(application)
