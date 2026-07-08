"""File upload handling: validation, storage, text extraction."""
from __future__ import annotations

import os
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.logging import get_logger, log_event
from app.models.document import Document
from app.models.timeline_event import TimelineSourceType
from app.models.user import User
from app.repositories.document_repo import DocumentRepository
from app.services.ai_service import AIService
from app.services.ocr_service import extract_text
from app.services.timeline_service import TimelineService

log = get_logger("francessca.files")

ALLOWED_MIMES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/tiff",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}


class FileService:
    def __init__(self, db: Session, ai: AIService | None = None) -> None:
        self.db = db
        self.documents = DocumentRepository(db)
        self.timeline = TimelineService(db, ai=ai)
        os.makedirs(settings.upload_dir, exist_ok=True)

    def save_upload(self, user: User, upload: UploadFile) -> Document:
        content = upload.file.read()
        size = len(content)

        if size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file"
            )
        if size > settings.max_upload_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds {settings.max_upload_size} bytes",
            )
        mime = upload.content_type or "application/octet-stream"
        if mime not in ALLOWED_MIMES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type: {mime}",
            )

        # Store under a per-user directory with a random name to avoid clashes
        # and path traversal via the original filename.
        user_dir = os.path.join(settings.upload_dir, str(user.id))
        os.makedirs(user_dir, exist_ok=True)
        safe_name = f"{uuid.uuid4().hex}{os.path.splitext(upload.filename or '')[1]}"
        stored_path = os.path.join(user_dir, safe_name)
        with open(stored_path, "wb") as fh:
            fh.write(content)

        extracted = extract_text(content, mime, upload.filename or safe_name)

        doc = Document(
            user_id=user.id,
            filename=os.path.basename(upload.filename or safe_name),
            stored_path=stored_path,
            size=size,
            mime=mime,
            extracted_text=extracted,
        )
        self.documents.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        log_event(
            log, "file_upload", user_id=user.id, doc_id=doc.id,
            size=size, mime=mime, ocr=bool(extracted),
        )

        # Best-effort: pull dated facts out of the document into the running
        # case timeline. Never raises — failures are logged and skipped.
        self.timeline.extract_from_text(
            user, extracted, source_type=TimelineSourceType.document, source_id=doc.id
        )
        self.db.commit()

        return doc
