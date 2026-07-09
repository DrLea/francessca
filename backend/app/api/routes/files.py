"""File upload, download, delete, and translated-download routes."""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.core.languages import SUPPORTED_LANGUAGES
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.repositories.document_repo import DocumentRepository
from app.schemas.common import DocumentOut, MessageResponse
from app.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["files"])


def _to_out(doc) -> DocumentOut:
    return DocumentOut(
        id=doc.id,
        filename=doc.filename,
        size=doc.size,
        mime=doc.mime,
        uploaded_at=doc.uploaded_at,
        has_extracted_text=bool(doc.extracted_text),
    )


@router.post("", response_model=DocumentOut)
def upload_file(
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentOut:
    doc = FileService(db).save_upload(user, file)
    return _to_out(doc)


@router.get("", response_model=list[DocumentOut])
def list_files(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[DocumentOut]:
    docs = DocumentRepository(db).list_for_user(user.id)
    return [_to_out(d) for d in docs]


@router.get("/{document_id}/download")
def download_file(
    document_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    """Download the original, as-uploaded file."""
    doc = FileService(db).get_owned(document_id, user.id)
    if not os.path.exists(doc.stored_path):
        raise HTTPException(
            status_code=status.HTTP_410_GONE, detail="File no longer available"
        )
    return FileResponse(doc.stored_path, media_type=doc.mime, filename=doc.filename)


@router.get("/{document_id}/translate")
def download_translated_file(
    document_id: int,
    lang: str = Query(..., description="Target language code, e.g. 'de'"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Translate the document's extracted text and return it as a downloadable
    PDF, in the requested (typically the caller's currently selected UI)
    language."""
    if lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language: {lang}",
        )
    filename, pdf_bytes = FileService(db).translate(user, document_id, lang)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{document_id}", response_model=MessageResponse)
def delete_file(
    document_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    FileService(db).delete(user, document_id)
    return MessageResponse(detail="Document deleted")
