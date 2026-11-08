"""Reply letters: a polite, firm letter in German to answer a German letter
or raise a problem (a landlord, a dorm office, an insurer), with the user's
photos and documents attached as evidence ("Anlagen"), plus a translation
into the user's language so they know exactly what they are sending.

One model call per draft. The letter states facts and requests only -- no
legal conclusions -- and the PDF ends with the usual recommendation to have
it reviewed by a lawyer when anything is at stake.
"""
from __future__ import annotations

import json
import re
from io import BytesIO

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.crypto import read_decrypted
from app.core.languages import LANGUAGE_NAMES, normalize_language
from app.core.prompts import USER_CONTENT_GUARD
from app.models.user import User
from app.repositories.document_repo import DocumentRepository
from app.services.ai_service import build_ai_service
from app.services.prompt_service import PromptService
from app.services.token_service import TokenService, estimate_tokens

IMAGE_MIMES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}

_INSTRUCTION = """Write a polite but firm formal letter in GERMAN (Sie-form,
standard German business-letter conventions) for the user described below.
Rules:
- State only facts the user gave. Do not invent dates, names, amounts or
  addresses; use clear placeholders like [Datum] or [Adresse] instead.
- Make concrete, reasonable requests (e.g. a reply by a date, a repair,
  a refund, documents) without legal conclusions or threats.
- If evidence is attached, refer to it in the text and list it at the end
  under "Anlagen" as numbered items using the given file names.
- Then translate the whole letter into {language} so the user understands it.
Return STRICT JSON only: {{"subject": "...", "german": "...", "translation": "..."}}"""


class ReplyService:
    def __init__(self, db: Session, ai=None) -> None:  # noqa: ANN001
        self.db = db
        self.ai = ai or build_ai_service()
        self.documents = DocumentRepository(db)
        self.prompts = PromptService(db)
        self.tokens = TokenService(db)

    def _documents(self, user: User, ids: list[int]):  # noqa: ANN202
        docs = []
        for doc_id in ids:
            doc = self.documents.get(doc_id)
            if doc is None or doc.user_id != user.id:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
            docs.append(doc)
        return docs

    def draft(
        self,
        user: User,
        *,
        situation: str,
        recipient: str | None,
        reply_to_document_id: int | None,
        evidence_document_ids: list[int],
    ) -> dict:
        evidence = self._documents(user, evidence_document_ids)
        letter = (
            self._documents(user, [reply_to_document_id])[0] if reply_to_document_id else None
        )
        language = LANGUAGE_NAMES.get(normalize_language(user.language), "English")
        parts = [USER_CONTENT_GUARD, f"Situation (user's words):\n{situation.strip()}"]
        if recipient:
            parts.append(f"Recipient: {recipient.strip()}")
        if letter is not None:
            parts.append(
                f"The letter being answered ({letter.filename}):\n"
                f"{(letter.extracted_text or '')[:6000]}"
            )
        if evidence:
            parts.append(
                "Evidence to attach:\n"
                + "\n".join(f"{i}. {d.filename}" for i, d in enumerate(evidence, 1))
            )
        parts.append(_INSTRUCTION.format(language=language))
        content = "\n\n".join(parts)

        self.tokens.ensure_within_limit(user, estimate_tokens(content) + 2000)
        result = self.ai.complete(
            system_prompt=self.prompts.active_system_prompt(),
            messages=[{"role": "user", "content": content}],
            max_tokens=2000,
        )
        self.tokens.record(
            user, input_tokens=result.input_tokens, output_tokens=result.output_tokens,
            model=result.model,
        )
        parsed = _parse(result.text)
        return {
            "subject": parsed.get("subject") or "Ihr Schreiben",
            "german": parsed.get("german") or result.text.strip(),
            "translation": parsed.get("translation") or "",
            "language": normalize_language(user.language),
            "evidence": [{"id": d.id, "filename": d.filename, "mime": d.mime} for d in evidence],
        }

    def render_pdf(self, user: User, subject: str, german: str, evidence_ids: list[int]) -> bytes:
        """The German letter, then each photo as an 'Anlage' page."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer
        from xml.sax.saxutils import escape

        evidence = self._documents(user, evidence_ids)
        styles = getSampleStyleSheet()
        font = "DejaVuSans"
        try:
            pdfmetrics.getFont(font)
        except Exception:  # noqa: BLE001
            font = "Helvetica"
        body = ParagraphStyle("B", parent=styles["BodyText"], fontName=font, leading=15)
        head = ParagraphStyle("H", parent=styles["Heading2"], fontName=font)
        small = ParagraphStyle("S", parent=body, fontSize=8, textColor="#666666")

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4, leftMargin=2.5 * cm, rightMargin=2 * cm,
            topMargin=2 * cm, bottomMargin=2 * cm, title=subject,
        )
        flow: list = [Paragraph(escape(f"Betreff: {subject}"), head), Spacer(1, 8)]
        for block in german.strip().split("\n\n"):
            flow.append(Paragraph(escape(block).replace("\n", "<br/>"), body))
            flow.append(Spacer(1, 6))
        flow.append(Spacer(1, 18))
        flow.append(Paragraph(
            "Erstellt mit Francesca. Keine Rechtsberatung - bei wichtigen Fragen "
            "bitte von einer Anwältin oder einem Anwalt prüfen lassen.", small,
        ))
        max_w, max_h = A4[0] - 4.5 * cm, A4[1] - 6 * cm
        for i, d in enumerate(evidence, 1):
            flow += [PageBreak(), Paragraph(escape(f"Anlage {i}: {d.filename}"), head)]
            if d.mime in IMAGE_MIMES:
                data = read_decrypted(d.stored_path)
                img = Image(BytesIO(data))
                scale = min(max_w / img.imageWidth, max_h / img.imageHeight, 1.0)
                img.drawWidth, img.drawHeight = img.imageWidth * scale, img.imageHeight * scale
                flow.append(img)
            else:
                flow.append(Paragraph(
                    escape((d.extracted_text or "(Dokument liegt bei)")[:3000]).replace("\n", "<br/>"),
                    body,
                ))
        doc.build(flow)
        return buffer.getvalue()


def _parse(text: str) -> dict:
    match = re.search(r"\{.*\}", text or "", re.S)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return {k: str(v) for k, v in data.items() if isinstance(v, (str, int, float))}
