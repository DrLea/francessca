"""Case generation and export routes."""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_data_consent
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



def _decrypted_response(path: str, media_type: str, filename: str) -> Response:
    """Files are encrypted at rest; decrypt in memory for the owner."""
    from urllib.parse import quote

    from app.core.crypto import read_decrypted

    return Response(
        content=read_decrypted(path),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )

router = APIRouter(prefix="/case", tags=["case"])


@router.get("/templates")
def list_templates(lang: str = "en") -> dict:
    return {
        "categories": CATEGORIES,
        "templates": [translate_template(t, lang) for t in TEMPLATES.values()],
    }


@router.get("/timeline/upcoming", response_model=list[TimelineEventOut])
def upcoming_timeline(
    days: int = 14,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TimelineEventOut]:
    """In-app reminders: dated entries in the next `days` days."""
    from datetime import date, timedelta

    today = date.today()
    horizon = today + timedelta(days=max(1, min(days, 90)))
    return [
        e for e in get_timeline(user=user, db=db)
        if e.event_date is not None and today <= e.event_date <= horizon
    ]


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
    user: User = Depends(require_data_consent),
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
    user: User = Depends(require_data_consent),
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
    user: User = Depends(require_data_consent),
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
) -> Response:
    from app.models.export import Export

    export = db.get(Export, export_id)
    if export is None or export.case is None or export.case.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not os.path.exists(export.stored_path):
        raise HTTPException(
            status_code=status.HTTP_410_GONE, detail="Export file no longer available"
        )
    media = "application/pdf" if export.kind.value == "pdf" else "application/zip"
    return _decrypted_response(export.stored_path, media, export.filename)


# --- Reply letters in German, with evidence ----------------------------------
class ReplyDraftRequest(BaseModel):
    situation: str = Field(min_length=10, max_length=6_000)
    recipient: str | None = Field(default=None, max_length=255)
    # The German letter being answered, if any (an uploaded document).
    reply_to_document_id: int | None = None
    # Photos / documents attached as "Anlagen".
    evidence_document_ids: list[int] = Field(default_factory=list, max_length=10)


class ReplyPdfRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=255)
    german: str = Field(min_length=1, max_length=20_000)
    evidence_document_ids: list[int] = Field(default_factory=list, max_length=10)


@router.post("/reply-draft")
def draft_reply(
    data: ReplyDraftRequest,
    user: User = Depends(require_data_consent),
    db: Session = Depends(get_db),
) -> dict:
    """A polite, firm German letter plus a translation into the user's
    language. One model call. The user reviews and edits it before use."""
    from app.services.reply_service import ReplyService

    return ReplyService(db).draft(
        user,
        situation=data.situation,
        recipient=data.recipient,
        reply_to_document_id=data.reply_to_document_id,
        evidence_document_ids=data.evidence_document_ids,
    )


@router.post("/reply-draft/pdf")
def reply_pdf(
    data: ReplyPdfRequest,
    user: User = Depends(require_data_consent),
    db: Session = Depends(get_db),
) -> Response:
    """The (possibly edited) German letter as a PDF, photos attached as
    Anlagen. Rendered on the fly and never stored."""
    from app.services.reply_service import ReplyService

    pdf = ReplyService(db).render_pdf(user, data.subject, data.german, data.evidence_document_ids)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="Brief.pdf"'},
    )
