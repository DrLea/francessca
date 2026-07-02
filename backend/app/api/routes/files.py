"""File upload routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.repositories.document_repo import DocumentRepository
from app.schemas.common import DocumentOut
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
