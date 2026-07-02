"""Case export: PDF summary and ZIP bundle of uploaded documents."""
from __future__ import annotations

import os
import zipfile
from io import BytesIO

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)
from sqlalchemy.orm import Session

from app.config import settings
from app.core.logging import get_logger, log_event
from app.models.case import Case
from app.models.export import Export, ExportKind
from app.repositories.document_repo import DocumentRepository, ExportRepository
from app.schemas.case import CaseSummary

log = get_logger("francessca.export")

_SECTION_ORDER = [
    ("case_type", "Case Type"),
    ("timeline", "Timeline"),
    ("people_involved", "People Involved"),
    ("important_dates", "Important Dates"),
    ("documents_available", "Documents Available"),
    ("missing_documents", "Missing Documents"),
    ("questions_for_lawyer", "Questions for Lawyer"),
    ("potential_relevant_topics", "Potential Relevant Topics"),
    ("generated_forms", "Generated Forms"),
    ("attachments", "Attachments"),
]

_DISCLAIMER = (
    "This document was prepared by Francessca, an AI assistant that helps organize "
    "facts. It is NOT legal advice. Please have these documents reviewed by a "
    "qualified lawyer."
)


class ExportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.documents = DocumentRepository(db)
        self.exports = ExportRepository(db)
        self._export_dir = os.path.join(settings.upload_dir, "exports")
        os.makedirs(self._export_dir, exist_ok=True)

    def build_pdf(self, case: Case) -> Export:
        summary = CaseSummary(**(case.summary or {}))
        pdf_bytes = self._render_pdf(case.title, summary)

        filename = f"case_{case.id}_summary.pdf"
        path = os.path.join(self._export_dir, filename)
        with open(path, "wb") as fh:
            fh.write(pdf_bytes)

        export = Export(
            case_id=case.id,
            kind=ExportKind.pdf,
            filename=filename,
            stored_path=path,
            size=len(pdf_bytes),
        )
        self.exports.add(export)
        self.db.commit()
        self.db.refresh(export)
        log_event(log, "export_pdf", case_id=case.id, size=len(pdf_bytes))
        return export

    def build_zip(self, case: Case, user_id: int) -> Export:
        """ZIP containing the PDF summary plus all uploaded documents."""
        pdf_export = self.build_pdf(case)
        docs = self.documents.list_for_user(user_id)

        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(pdf_export.stored_path, arcname="00_case_summary.pdf")
            for i, doc in enumerate(docs, start=1):
                if os.path.exists(doc.stored_path):
                    zf.write(
                        doc.stored_path,
                        arcname=f"documents/{i:02d}_{doc.filename}",
                    )

        filename = f"case_{case.id}_bundle.zip"
        path = os.path.join(self._export_dir, filename)
        data = buffer.getvalue()
        with open(path, "wb") as fh:
            fh.write(data)

        export = Export(
            case_id=case.id,
            kind=ExportKind.zip,
            filename=filename,
            stored_path=path,
            size=len(data),
        )
        self.exports.add(export)
        self.db.commit()
        self.db.refresh(export)
        log_event(log, "export_zip", case_id=case.id, size=len(data))
        return export

    def _render_pdf(self, title: str, summary: CaseSummary) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            topMargin=2 * cm, bottomMargin=2 * cm,
            leftMargin=2 * cm, rightMargin=2 * cm,
            title=title,
        )
        styles = getSampleStyleSheet()
        h1 = ParagraphStyle("H1", parent=styles["Title"], fontSize=20)
        h2 = ParagraphStyle("H2", parent=styles["Heading2"], spaceBefore=12)
        body = ParagraphStyle("Body", parent=styles["BodyText"], alignment=TA_LEFT)
        small = ParagraphStyle("Small", parent=styles["BodyText"], fontSize=8,
                               textColor="#666666")

        flow: list = [Paragraph(title or "Case Summary", h1), Spacer(1, 6)]
        flow.append(Paragraph(_DISCLAIMER, small))
        flow.append(Spacer(1, 12))

        data = summary.model_dump()
        for key, label in _SECTION_ORDER:
            value = data.get(key)
            if not value:
                continue
            flow.append(Paragraph(label, h2))
            if isinstance(value, list):
                items = [ListItem(Paragraph(str(v), body)) for v in value]
                flow.append(ListFlowable(items, bulletType="bullet"))
            else:
                flow.append(Paragraph(str(value), body))

        if summary.narrative:
            flow.append(Paragraph("Summary", h2))
            flow.append(Paragraph(summary.narrative.replace("\n", "<br/>"), body))

        flow.append(Spacer(1, 18))
        flow.append(Paragraph(_DISCLAIMER, small))

        doc.build(flow)
        return buffer.getvalue()
