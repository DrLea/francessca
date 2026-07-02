"""Text extraction from uploaded files (OCR for images, parsing for docs)."""
from __future__ import annotations

import io

from app.core.logging import get_logger

log = get_logger("francessca.ocr")

IMAGE_MIMES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/tiff"}


def extract_text(content: bytes, mime: str, filename: str) -> str | None:
    """Best-effort text extraction. Returns None if nothing could be read.

    Heavy/optional dependencies (pytesseract, pypdf, python-docx) are imported
    lazily so the rest of the app works even if one is unavailable.
    """
    try:
        if mime in IMAGE_MIMES:
            return _ocr_image(content)
        if mime == "application/pdf" or filename.lower().endswith(".pdf"):
            return _extract_pdf(content)
        if mime in (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ) or filename.lower().endswith(".docx"):
            return _extract_docx(content)
        if mime.startswith("text/") or filename.lower().endswith(".txt"):
            return content.decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001 - extraction is best effort
        log.warning("text extraction failed for %s: %s", filename, exc)
    return None


def _ocr_image(content: bytes) -> str | None:
    import pytesseract
    from PIL import Image

    image = Image.open(io.BytesIO(content))
    # German + English coverage for the target market.
    text = pytesseract.image_to_string(image, lang="deu+eng")
    return text.strip() or None


def _extract_pdf(content: bytes) -> str | None:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    parts = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(parts).strip()
    return text or None


def _extract_docx(content: bytes) -> str | None:
    import docx

    document = docx.Document(io.BytesIO(content))
    text = "\n".join(p.text for p in document.paragraphs).strip()
    return text or None
