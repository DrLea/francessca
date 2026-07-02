"""Lawyer directory & search routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.repositories.lawyer_repo import LawyerRepository
from app.schemas.lawyer import LawyerOut, LawyerSearchResult
from app.services.lawyer_service import LawyerService

router = APIRouter(prefix="/lawyers", tags=["lawyers"])


@router.get("", response_model=LawyerSearchResult)
def list_lawyers(
    limit: int = Query(20, le=100),
    offset: int = 0,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LawyerSearchResult:
    total, rows = LawyerService(db).search(limit=limit, offset=offset)
    return LawyerSearchResult(
        total=total, items=[LawyerOut.model_validate(r) for r in rows]
    )


@router.get("/search", response_model=LawyerSearchResult)
def search_lawyers(
    specialization: str | None = None,
    city: str | None = None,
    language: str | None = None,
    limit: int = Query(20, le=100),
    offset: int = 0,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LawyerSearchResult:
    total, rows = LawyerService(db).search(
        specialization=specialization,
        city=city,
        language=language,
        limit=limit,
        offset=offset,
    )
    return LawyerSearchResult(
        total=total, items=[LawyerOut.model_validate(r) for r in rows]
    )


@router.get("/{lawyer_id}", response_model=LawyerOut)
def get_lawyer(
    lawyer_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LawyerOut:
    lawyer = LawyerRepository(db).get(lawyer_id)
    if lawyer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return LawyerOut.model_validate(lawyer)
