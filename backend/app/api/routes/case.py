"""Case generation and export routes."""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.repositories.document_repo import CaseRepository
from app.schemas.case import CaseExportRequest, CaseOut
from app.services.case_service import CaseService
from app.services.export_service import ExportService
from app.services.templates import CATEGORIES, TEMPLATES

router = APIRouter(prefix="/case", tags=["case"])


@router.get("/templates")
def list_templates() -> dict:
    return {
        "categories": CATEGORIES,
        "templates": [
            {
                "id": t.id,
                "category": t.category,
                "title": t.title,
                "description": t.description,
                "fields": [
                    {"key": f.key, "label": f.label, "required": f.required}
                    for f in t.fields
                ],
            }
            for t in TEMPLATES.values()
        ],
    }


@router.post("/summary", response_model=CaseOut)
def generate_summary(
    conversation_id: int,
    title: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseOut:
    case = CaseService(db).generate_summary(user, conversation_id, title)
    return CaseOut.model_validate(case)


@router.get("", response_model=list[CaseOut])
def list_cases(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[CaseOut]:
    cases = CaseRepository(db).list_for_user(user.id)
    return [CaseOut.model_validate(c) for c in cases]


@router.post("/export")
def export_case(
    data: CaseExportRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Generate a fresh case summary then build PDF (+ optional ZIP)."""
    case = CaseService(db).generate_summary(user, data.conversation_id, data.title)
    export_service = ExportService(db)
    pdf = export_service.build_pdf(case)
    result = {"case_id": case.id, "pdf_export_id": pdf.id}
    if data.include_documents:
        zip_export = export_service.build_zip(case, user.id)
        result["zip_export_id"] = zip_export.id
    return result


@router.get("/export/{export_id}/download")
def download_export(
    export_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    from app.models.export import Export

    export = db.get(Export, export_id)
    if export is None or export.case is None or export.case.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not os.path.exists(export.stored_path):
        raise HTTPException(
            status_code=status.HTTP_410_GONE, detail="Export file no longer available"
        )
    media = "application/pdf" if export.kind.value == "pdf" else "application/zip"
    return FileResponse(export.stored_path, media_type=media, filename=export.filename)
