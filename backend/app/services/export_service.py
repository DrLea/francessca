"""Case export: PDF summary and ZIP bundle of uploaded documents."""
from __future__ import annotations

import os
import zipfile
from io import BytesIO

from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)
from sqlalchemy.orm import Session

from app.core.crypto import read_decrypted, write_encrypted
from app.config import settings
from app.core.languages import normalize_language
from app.core.logging import get_logger, log_event
from app.models.case import Case
from app.models.export import Export, ExportKind
from app.repositories.document_repo import DocumentRepository, ExportRepository
from app.schemas.case import CaseSummary
from app.services.timeline_service import TimelineService

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

# Section-label and disclaimer translations. Same caveat as templates.py:
# first-pass translations, worth a native-speaker review before production.
_SECTION_LABEL_TRANSLATIONS: dict[str, dict[str, str]] = {
    "Case Type": {"de": "Art des Falls", "tr": "Dava Türü", "ar": "نوع القضية",
                  "uk": "Тип справи", "ru": "Тип дела", "pl": "Rodzaj sprawy", "ro": "Tipul cazului"},
    "Timeline": {"de": "Zeitverlauf", "tr": "Zaman Çizelgesi", "ar": "الجدول الزمني",
                 "uk": "Хронологія", "ru": "Хронология", "pl": "Chronologia", "ro": "Cronologie"},
    "People Involved": {"de": "Beteiligte Personen", "tr": "İlgili Kişiler", "ar": "الأشخاص المعنيون",
                         "uk": "Причетні особи", "ru": "Причастные лица", "pl": "Osoby zaangażowane",
                         "ro": "Persoane implicate"},
    "Important Dates": {"de": "Wichtige Termine", "tr": "Önemli Tarihler", "ar": "تواريخ مهمة",
                         "uk": "Важливі дати", "ru": "Важные даты", "pl": "Ważne daty", "ro": "Date importante"},
    "Documents Available": {"de": "Vorhandene Unterlagen", "tr": "Mevcut Belgeler", "ar": "المستندات المتوفرة",
                             "uk": "Наявні документи", "ru": "Имеющиеся документы", "pl": "Dostępne dokumenty",
                             "ro": "Documente disponibile"},
    "Missing Documents": {"de": "Fehlende Unterlagen", "tr": "Eksik Belgeler", "ar": "المستندات الناقصة",
                          "uk": "Відсутні документи", "ru": "Отсутствующие документы",
                          "pl": "Brakujące dokumenty", "ro": "Documente lipsă"},
    "Questions for Lawyer": {"de": "Fragen an den Anwalt", "tr": "Avukata Sorular", "ar": "أسئلة للمحامي",
                              "uk": "Питання до адвоката", "ru": "Вопросы адвокату",
                              "pl": "Pytania do prawnika", "ro": "Întrebări pentru avocat"},
    "Potential Relevant Topics": {"de": "Möglicherweise relevante Themen", "tr": "Olası İlgili Konular",
                                   "ar": "مواضيع قد تكون ذات صلة", "uk": "Можливо релевантні теми",
                                   "ru": "Возможно релевантные темы", "pl": "Potencjalnie istotne kwestie",
                                   "ro": "Subiecte potențial relevante"},
    "Generated Forms": {"de": "Erstellte Formulare", "tr": "Oluşturulan Formlar", "ar": "النماذج التي تم إنشاؤها",
                         "uk": "Створені форми", "ru": "Созданные формы", "pl": "Wygenerowane formularze",
                         "ro": "Formulare generate"},
    "Attachments": {"de": "Anhänge", "tr": "Ekler", "ar": "المرفقات", "uk": "Додатки", "ru": "Приложения",
                    "pl": "Załączniki", "ro": "Anexe"},
    "Summary": {"de": "Zusammenfassung", "tr": "Özet", "ar": "الملخص", "uk": "Резюме", "ru": "Резюме",
                "pl": "Podsumowanie", "ro": "Rezumat"},
}

_DISCLAIMER_TRANSLATIONS: dict[str, str] = {
    "de": (
        "Dieses Dokument wurde von Francesca erstellt, einem KI-Assistenten, der Fakten "
        "organisiert. Es ist KEINE Rechtsberatung. Bitte lassen Sie diese Unterlagen von "
        "einem qualifizierten Anwalt prüfen."
    ),
    "tr": (
        "Bu belge, gerçekleri düzenlemeye yardımcı olan bir yapay zeka asistanı olan "
        "Francesca tarafından hazırlanmıştır. Bu bir HUKUKİ TAVSİYE DEĞİLDİR. Lütfen bu "
        "belgeleri yetkin bir avukata inceletin."
    ),
    "ar": (
        "تم إعداد هذا المستند بواسطة Francesca، وهو مساعد ذكاء اصطناعي يساعد في تنظيم "
        "الوقائع. هذا ليس استشارة قانونية. يرجى مراجعة هذه المستندات من قبل محامٍ مؤهل."
    ),
    "uk": (
        "Цей документ підготовано Francesca, ШІ-асистентом, який допомагає "
        "організовувати факти. Це НЕ юридична консультація. Будь ласка, попросіть "
        "кваліфікованого юриста перевірити ці документи."
    ),
    "ru": (
        "Этот документ подготовлен Francesca, ИИ-ассистентом, который помогает "
        "организовывать факты. Это НЕ юридическая консультация. Пожалуйста, попросите "
        "квалифицированного юриста проверить эти документы."
    ),
    "pl": (
        "Ten dokument został przygotowany przez Francesca, asystenta AI pomagającego "
        "uporządkować fakty. To NIE jest porada prawna. Prosimy o sprawdzenie tych "
        "dokumentów przez wykwalifikowanego prawnika."
    ),
    "ro": (
        "Acest document a fost pregătit de Francesca, un asistent AI care ajută la "
        "organizarea faptelor. NU reprezintă consultanță juridică. Vă rugăm ca aceste "
        "documente să fie verificate de un avocat calificat."
    ),
}

_DISCLAIMER = (
    "This document was prepared by Francesca, an AI assistant that helps organize "
    "facts. It is NOT legal advice. Please have these documents reviewed by a "
    "qualified lawyer."
)


def _section_label(label: str, lang: str) -> str:
    lang = normalize_language(lang)
    if lang == "en":
        return label
    return _SECTION_LABEL_TRANSLATIONS.get(label, {}).get(lang, label)


RTL_LANGUAGES = {"ar"}


def _visual_rtl(text: str) -> str:
    """Arabic for reportlab, which lays text out left to right and does not
    join letters: reshape to presentation forms, reorder each line with the
    Unicode bidi algorithm, escape, and keep line breaks as <br/>."""
    from xml.sax.saxutils import escape

    import arabic_reshaper
    from bidi.algorithm import get_display

    lines = str(text).replace("<br/>", "\n").split("\n")
    return "<br/>".join(escape(get_display(arabic_reshaper.reshape(line))) for line in lines)


def _disclaimer(lang: str) -> str:
    lang = normalize_language(lang)
    return _DISCLAIMER if lang == "en" else _DISCLAIMER_TRANSLATIONS.get(lang, _DISCLAIMER)


# Public alias — reused by other services (e.g. FileService's translated-document
# download) that need the same disclaimer copy without duplicating it.
disclaimer_text = _disclaimer


class ExportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.documents = DocumentRepository(db)
        self.exports = ExportRepository(db)
        self.timeline = TimelineService(db)
        self._export_dir = os.path.join(settings.upload_dir, "exports")
        os.makedirs(self._export_dir, exist_ok=True)

    def build_pdf(self, case: Case) -> Export:
        summary = CaseSummary(**(case.summary or {}))
        lang = case.user.language if case.user else "en"
        events = self.timeline.list_for_user(case.user_id)
        pdf_bytes = self._render_pdf(case.title, summary, lang, events)

        filename = f"case_{case.id}_summary.pdf"
        path = os.path.join(self._export_dir, filename)
        write_encrypted(path, pdf_bytes)

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
            zf.writestr("00_case_summary.pdf", read_decrypted(pdf_export.stored_path))
            for i, doc in enumerate(docs, start=1):
                if os.path.exists(doc.stored_path):
                    zf.writestr(
                        f"documents/{i:02d}_{doc.filename}",
                        read_decrypted(doc.stored_path),
                    )

        filename = f"case_{case.id}_bundle.zip"
        path = os.path.join(self._export_dir, filename)
        data = buffer.getvalue()
        write_encrypted(path, data)

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

    def _render_pdf(
        self,
        title: str,
        summary: CaseSummary,
        lang: str = "en",
        events: list | None = None,
    ) -> bytes:
        """Render the case-summary PDF.

        Uses DejaVu fonts when available for Unicode (Cyrillic, Arabic, ...).
        Arabic is reshaped, reordered right-to-left and right-aligned.
        """
        rtl = normalize_language(lang) in RTL_LANGUAGES
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            topMargin=2 * cm, bottomMargin=2 * cm,
            leftMargin=2 * cm, rightMargin=2 * cm,
            title=title,
        )
        styles = getSampleStyleSheet()
        # Use DejaVu font if registered, otherwise fall back to default.
        font_name = "DejaVuSans"
        try:
            pdfmetrics.getFont(font_name)
        except Exception:
            font_name = "Helvetica"
        h1 = ParagraphStyle("H1", parent=styles["Title"], fontSize=20, fontName=font_name)
        h2 = ParagraphStyle("H2", parent=styles["Heading2"], spaceBefore=12, fontName=font_name)
        body = ParagraphStyle("Body", parent=styles["BodyText"], alignment=TA_LEFT, fontName=font_name)
        small = ParagraphStyle("Small", parent=styles["BodyText"], fontSize=8,
                               textColor="#666666", fontName=font_name)
        if rtl:
            for style in (h1, h2, body, small):
                style.alignment = TA_RIGHT

        def para(text: str, style: ParagraphStyle) -> Paragraph:
            return Paragraph(_visual_rtl(text) if rtl else text, style)

        disclaimer = _disclaimer(lang)

        flow: list = [para(title or "Case Summary", h1), Spacer(1, 6)]
        flow.append(para(disclaimer, small))
        flow.append(Spacer(1, 12))

        data = summary.model_dump()
        for key, label in _SECTION_ORDER:
            translated_label = _section_label(label, lang)

            if key == "timeline" and events:
                # Prefer the structured, auto-extracted timeline (real dates,
                # deadline flags) over the AI summary's free-form string list.
                flow.append(para(translated_label, h2))
                items = [
                    ListItem(
                        para(
                            (
                                f"{e.event_date.isoformat() if e.event_date else e.date_label or '—'}"
                                f" — {e.description}"
                                if rtl
                                else f"<b>{e.event_date.isoformat() if e.event_date else e.date_label or '—'}"
                                f"</b> — {e.description}"
                            )
                            + (" [DEADLINE]" if e.is_deadline else ""),
                            body,
                        )
                    )
                    for e in events
                ]
                flow.append(ListFlowable(items, bulletType="bullet"))
                continue

            value = data.get(key)
            if not value:
                continue
            flow.append(para(translated_label, h2))
            if isinstance(value, list):
                items = [ListItem(para(str(v), body)) for v in value]
                flow.append(ListFlowable(items, bulletType="bullet"))
            else:
                flow.append(para(str(value), body))

        if summary.narrative:
            flow.append(para(_section_label("Summary", lang), h2))
            flow.append(para(summary.narrative.replace("\n", "<br/>"), body))

        flow.append(Spacer(1, 18))
        flow.append(para(disclaimer, small))

        doc.build(flow)
        return buffer.getvalue()
