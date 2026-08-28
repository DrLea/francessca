"""Case generation and export routes."""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.timeline_event import TimelineSourceType
from app.models.user import User
from app.repositories.conversation_repo import ConversationRepository
from app.repositories.document_repo import CaseRepository, DocumentRepository
from app.schemas.case import CaseExportRequest, CaseOut
from app.schemas.timeline import TimelineEventCreate, TimelineEventOut
from app.services.case_service import CaseService
from app.services.export_service import ExportService
from app.services.templates import CATEGORIES, TEMPLATES, translate_template
from app.services.timeline_service import TimelineService

router = APIRouter(prefix="/case", tags=["case"])


@router.get("/templates")
def list_templates(lang: str = "en") -> dict:
    return {
        "categories": CATEGORIES,
        "templates": [translate_template(t, lang) for t in TEMPLATES.values()],
    }


@router.get("/timeline", response_model=list[TimelineEventOut])
def get_timeline(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[TimelineEventOut]:
    """The auto-extracted calendar: appointments, hearings, deadlines and
    expiry dates found in the user's documents and chat messages. Every
    entry carries the document or conversation it came from."""
    events = TimelineService(db).list_for_user(user.id)

    doc_ids = [
        e.source_id
        for e in events
        if e.source_type is TimelineSourceType.document and e.source_id
    ]
    docs = (
        {
            d.id: d.filename
            for d in DocumentRepository(db).get_many_for_user(doc_ids, user.id)
        }
        if doc_ids
        else {}
    )
    convs = (
        {c.id: c.title for c in ConversationRepository(db).list_for_user(user.id)}
        if any(e.conversation_id for e in events)
        else {}
    )

    items: list[TimelineEventOut] = []
    for e in events:
        item = TimelineEventOut.model_validate(e)
        # A deleted document or conversation simply leaves the entry unlinked.
        if e.source_type is TimelineSourceType.document:
            item.source_label = docs.get(e.source_id)
        elif e.conversation_id:
            item.source_label = convs.get(e.conversation_id)
        items.append(item)
    return items


@router.post(
    "/timeline", response_model=TimelineEventOut, status_code=status.HTTP_201_CREATED
)
def create_timeline_event(
    data: TimelineEventCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TimelineEventOut:
    """Add an entry by hand — for anything the extractor missed."""
    event = TimelineService(db).add_manual(
        user,
        event_date=data.event_date,
        description=data.description,
        is_deadline=data.is_deadline,
    )
    return TimelineEventOut.model_validate(event)


@router.delete("/timeline/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_timeline_event(
    event_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Remove one entry the extractor got wrong or the user no longer needs."""
    if not TimelineService(db).delete_for_user(event_id, user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
