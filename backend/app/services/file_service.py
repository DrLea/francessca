"""File upload handling: validation, storage, text extraction, translation."""
from __future__ import annotations

import html
import os
import uuid
from io import BytesIO

from fastapi import HTTPException, UploadFile, status
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy.orm import Session

from app.config import settings
from app.core.languages import normalize_language, translation_instruction
from app.core.logging import get_logger, log_event
from app.core.prompts import FRANCESSCA_SYSTEM_PROMPT, USER_CONTENT_GUARD
from app.models.document import Document
from app.models.timeline_event import TimelineSourceType
from app.models.user import User
from app.repositories.document_repo import DocumentRepository
from app.services.ai_service import AIService
from app.services.export_service import disclaimer_text
from app.services.ocr_service import extract_text
from app.services.timeline_service import TimelineService
from app.services.token_service import TokenService, estimate_tokens

log = get_logger("francessca.files")

# Register DejaVu fonts for better Unicode support (Cyrillic, Greek, etc).
# DejaVu is widely available and bundled with reportlab on many systems.
def _register_dejavu_fonts() -> None:
    """Register DejaVu TrueType fonts for multilingual PDF rendering.

    DejaVu fonts support Latin, Cyrillic, Greek, and many other scripts,
    making them suitable for translated documents in those languages.
    Silently skips if fonts aren't found (fallback to default reporting
    behavior — text may be missing but won't crash).
    """
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
        "/System/Library/Fonts/DejaVuSans.ttf",  # macOS
        "C:\\Windows\\Fonts\\DejaVuSans.ttf",  # Windows
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("DejaVuSans", path))
                pdfmetrics.registerFont(
                    TTFont(
                        "DejaVuSans-Bold",
                        path.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"),
                    )
                )
                return
            except Exception as e:
                log.debug("font_registration_failed", extra={"path": path, "error": str(e)})
                continue
    log.warning("dejavu_fonts_not_found")


_register_dejavu_fonts()

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
        self.ai = ai or AIService()
        self.timeline = TimelineService(db, ai=self.ai)
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

    def get_owned(self, doc_id: int, user_id: int) -> Document:
        """Fetch a document, raising 404 if it doesn't exist or belongs to
        someone else (kept indistinguishable so ownership can't be probed)."""
        doc = self.documents.get(doc_id)
        if doc is None or doc.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
            )
        return doc

    def delete(self, user: User, doc_id: int) -> None:
        doc = self.get_owned(doc_id, user.id)
        if os.path.exists(doc.stored_path):
            try:
                os.remove(doc.stored_path)
            except OSError:
                log.warning(
                    "file_delete_disk_failed", extra={"doc_id": doc.id, "user_id": user.id}
                )
        self.documents.delete(doc)
        self.db.commit()
        log_event(log, "file_delete", user_id=user.id, doc_id=doc_id)

    def translate(self, user: User, doc_id: int, lang: str) -> tuple[str, bytes]:
        """Translate a previously extracted document's text into `lang` and
        render it as a downloadable PDF. Never persisted server-side — built
        fresh on each request, same as a live case export."""
        doc = self.get_owned(doc_id, user.id)
        source_text = (doc.extracted_text or "").strip()
        if not source_text:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No extracted text available to translate for this document",
            )

        lang = normalize_language(lang)
        system_prompt = FRANCESSCA_SYSTEM_PROMPT + translation_instruction(lang)
        user_content = f"{USER_CONTENT_GUARD}\n\n{source_text}"

        tokens = TokenService(self.db)
        source_tokens = estimate_tokens(source_text)
        estimated = estimate_tokens(system_prompt) + source_tokens * 2 + 256
        tokens.ensure_within_limit(user, estimated)

        result = self.ai.complete(
            system_prompt=system_prompt,
            messages=[{"role": "user", "content": user_content}],
            max_tokens=min(8192, source_tokens * 2 + 512),
        )

        tokens.record(
            user, input_tokens=result.input_tokens, output_tokens=result.output_tokens,
            model=result.model,
        )
        self.db.commit()

        pdf_bytes = _render_translation_pdf(doc.filename, lang, result.text)
        stem = os.path.splitext(doc.filename)[0]
        filename = f"{stem}_{lang}.pdf"
        log_event(log, "file_translate", user_id=user.id, doc_id=doc_id, lang=lang)
        return filename, pdf_bytes


def _render_translation_pdf(original_filename: str, lang: str, translated_text: str) -> bytes:
    """Minimal single-document PDF: title, disclaimer, translated body.

    Uses DejaVu fonts when available for better Unicode support (Cyrillic, Greek, etc).
    Arabic text is rendered as-is without bidi reshaping (RTL layout not yet implemented).
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
        title=f"Translation: {original_filename}",
    )
    styles = getSampleStyleSheet()
    # Use DejaVu font if registered, otherwise fall back to default.
    font_name = "DejaVuSans"
    try:
        # Test if font is registered by asking pdfmetrics.
        pdfmetrics.getFont(font_name)
    except Exception:
        font_name = "Helvetica"
    h1 = ParagraphStyle("H1", parent=styles["Title"], fontSize=16, fontName=font_name)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontName=font_name)
    small = ParagraphStyle("Small", parent=styles["BodyText"], fontSize=8, textColor="#666666", fontName=font_name)

    disclaimer = disclaimer_text(lang)
    # Escape user/AI-derived content before feeding it to reportlab's
    # XML-flavored Paragraph markup, then restore paragraph breaks.
    safe_body = html.escape(translated_text).replace("\n", "<br/>")

    flow = [
        Paragraph(html.escape(original_filename), h1),
        Spacer(1, 6),
        Paragraph(disclaimer, small),
        Spacer(1, 12),
        Paragraph(safe_body, body),
        Spacer(1, 18),
        Paragraph(disclaimer, small),
    ]
    doc.build(flow)
    return buffer.getvalue()
