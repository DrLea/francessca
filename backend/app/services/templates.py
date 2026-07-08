"""Legal form/letter templates.

Each template declares the fields the AI must collect. The architecture is
data-driven so new categories can be added without code changes elsewhere.
These are generic, publicly-available form structures — NOT legal advice.

Field labels, titles, and descriptions are translated via `_TRANSLATIONS`,
keyed by the canonical English string with a fallback to English for any
language/string combination that isn't covered. This is a first-pass
translation set aimed at making the form usable for non-German/English
speakers immediately; it has not been reviewed by a native speaker in each
language and should get that review before being relied on in production,
especially for legal terminology in AR/UK/RU/PL/RO.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core.languages import normalize_language


@dataclass(frozen=True)
class FormField:
    key: str
    label: str
    required: bool = True


@dataclass(frozen=True)
class FormTemplate:
    id: str
    category: str
    title: str
    description: str
    fields: list[FormField] = field(default_factory=list)


def _f(key: str, label: str, required: bool = True) -> FormField:
    return FormField(key=key, label=label, required=required)


TEMPLATES: dict[str, FormTemplate] = {
    "employment_termination_response": FormTemplate(
        id="employment_termination_response",
        category="Employment",
        title="Response to Termination (factual letter)",
        description="A factual letter acknowledging a termination and requesting documents.",
        fields=[
            _f("full_name", "Your full name"),
            _f("employer_name", "Employer name"),
            _f("employment_start", "Employment start date"),
            _f("termination_date", "Termination date"),
            _f("contract_type", "Contract type"),
            _f("monthly_salary", "Monthly salary", required=False),
            _f("desired_outcome", "Desired outcome"),
        ],
    ),
    "immigration_general": FormTemplate(
        id="immigration_general",
        category="Immigration",
        title="Immigration matter intake",
        description="General intake for immigration / residence matters.",
        fields=[
            _f("full_name", "Your full name"),
            _f("nationality", "Nationality"),
            _f("current_status", "Current residence status"),
            _f("permit_type", "Permit/visa type"),
            _f("relevant_dates", "Relevant dates"),
            _f("desired_outcome", "Desired outcome"),
        ],
    ),
    "rental_defect_notice": FormTemplate(
        id="rental_defect_notice",
        category="Rental",
        title="Rental defect notice (Mängelanzeige)",
        description="Factual notice to a landlord describing a defect.",
        fields=[
            _f("tenant_name", "Tenant name"),
            _f("landlord_name", "Landlord name"),
            _f("property_address", "Property address"),
            _f("defect_description", "Description of the defect"),
            _f("defect_noticed_date", "Date defect was noticed"),
            _f("requested_remedy", "Requested remedy"),
        ],
    ),
    "consumer_complaint": FormTemplate(
        id="consumer_complaint",
        category="Consumer",
        title="Consumer complaint letter",
        description="Factual complaint about a product or service.",
        fields=[
            _f("full_name", "Your full name"),
            _f("company_name", "Company name"),
            _f("order_reference", "Order/invoice reference"),
            _f("purchase_date", "Purchase date"),
            _f("issue_description", "Description of the issue"),
            _f("requested_remedy", "Requested remedy"),
        ],
    ),
}

CATEGORIES = sorted({t.category for t in TEMPLATES.values()})


# English string -> {language code -> translation}. `en` never needs an
# entry (it IS the key); missing entries fall back to the English string.
_TRANSLATIONS: dict[str, dict[str, str]] = {
    "Response to Termination (factual letter)": {
        "de": "Antwort auf die Kündigung (Sachverhaltsschreiben)",
        "tr": "Fesihe Yanıt (bilgilendirme yazısı)",
        "ar": "الرد على الفصل من العمل (خطاب توضيحي بالوقائع)",
        "uk": "Відповідь на звільнення (фактичний лист)",
        "ru": "Ответ на увольнение (фактическое письмо)",
        "pl": "Odpowiedź na wypowiedzenie (pismo informacyjne)",
        "ro": "Răspuns la concediere (scrisoare factuală)",
    },
    "Immigration matter intake": {
        "de": "Aufnahme einer Einwanderungsangelegenheit",
        "tr": "Göçmenlik konusu ön bilgi formu",
        "ar": "استمارة أولية لمسألة الهجرة",
        "uk": "Первинна анкета з питань імміграції",
        "ru": "Первичная анкета по вопросам иммиграции",
        "pl": "Formularz wstępny w sprawie imigracyjnej",
        "ro": "Formular preliminar pentru o problemă de imigrare",
    },
    "Rental defect notice (Mängelanzeige)": {
        "de": "Mängelanzeige",
        "tr": "Kira Ayıbı Bildirimi",
        "ar": "إخطار بعيب في العقار المستأجر",
        "uk": "Повідомлення про несправність орендованого житла",
        "ru": "Уведомление о недостатке арендованного жилья",
        "pl": "Zgłoszenie usterki w wynajmowanym lokalu",
        "ro": "Notificare privind un defect al chiriei",
    },
    "Consumer complaint letter": {
        "de": "Verbraucherbeschwerde",
        "tr": "Tüketici Şikayet Mektubu",
        "ar": "خطاب شكوى المستهلك",
        "uk": "Лист-скарга споживача",
        "ru": "Письмо-жалоба потребителя",
        "pl": "Pismo reklamacyjne konsumenta",
        "ro": "Scrisoare de reclamație a consumatorului",
    },
    "A factual letter acknowledging a termination and requesting documents.": {
        "de": "Ein sachliches Schreiben, das die Kündigung bestätigt und Unterlagen anfordert.",
        "tr": "Feshi kabul eden ve belge talep eden bilgilendirici bir mektup.",
        "ar": "خطاب يوضح الوقائع يقر بالفصل من العمل ويطلب المستندات.",
        "uk": "Фактичний лист, що підтверджує звільнення та вимагає документи.",
        "ru": "Фактическое письмо, подтверждающее увольнение и запрашивающее документы.",
        "pl": "Pismo informacyjne potwierdzające wypowiedzenie i żądające dokumentów.",
        "ro": "O scrisoare factuală care confirmă concedierea și solicită documente.",
    },
    "General intake for immigration / residence matters.": {
        "de": "Allgemeine Erfassung für Einwanderungs-/Aufenthaltsangelegenheiten.",
        "tr": "Göçmenlik/oturum konuları için genel ön bilgi formu.",
        "ar": "استمارة أولية عامة لمسائل الهجرة/الإقامة.",
        "uk": "Загальна первинна анкета з питань імміграції/проживання.",
        "ru": "Общая первичная анкета по вопросам иммиграции/проживания.",
        "pl": "Ogólny formularz wstępny dla spraw imigracyjnych/pobytowych.",
        "ro": "Formular preliminar general pentru probleme de imigrare/ședere.",
    },
    "Factual notice to a landlord describing a defect.": {
        "de": "Ein sachliches Schreiben an den Vermieter zur Beschreibung eines Mangels.",
        "tr": "Ev sahibine ayıbı açıklayan bilgilendirici bir bildirim.",
        "ar": "إخطار يوضح الوقائع لصاحب العقار يصف عيبًا.",
        "uk": "Фактичне повідомлення орендодавцю з описом несправності.",
        "ru": "Фактическое уведомление арендодателю с описанием недостатка.",
        "pl": "Pismo informacyjne do wynajmującego opisujące usterkę.",
        "ro": "Notificare factuală către proprietar care descrie un defect.",
    },
    "Factual complaint about a product or service.": {
        "de": "Eine sachliche Beschwerde über ein Produkt oder eine Dienstleistung.",
        "tr": "Bir ürün veya hizmetle ilgili bilgilendirici bir şikayet.",
        "ar": "شكوى توضح الوقائع بشأن منتج أو خدمة.",
        "uk": "Фактична скарга щодо товару чи послуги.",
        "ru": "Фактическая жалоба на товар или услугу.",
        "pl": "Reklamacja dotycząca produktu lub usługi.",
        "ro": "Reclamație factuală privind un produs sau serviciu.",
    },
    "Your full name": {
        "de": "Ihr vollständiger Name",
        "tr": "Adınız soyadınız",
        "ar": "اسمك الكامل",
        "uk": "Ваше повне ім'я",
        "ru": "Ваше полное имя",
        "pl": "Twoje imię i nazwisko",
        "ro": "Numele tău complet",
    },
    "Employer name": {
        "de": "Name des Arbeitgebers",
        "tr": "İşveren adı",
        "ar": "اسم صاحب العمل",
        "uk": "Назва роботодавця",
        "ru": "Название работодателя",
        "pl": "Nazwa pracodawcy",
        "ro": "Numele angajatorului",
    },
    "Employment start date": {
        "de": "Beginn des Beschäftigungsverhältnisses",
        "tr": "İşe başlama tarihi",
        "ar": "تاريخ بدء العمل",
        "uk": "Дата початку роботи",
        "ru": "Дата начала работы",
        "pl": "Data rozpoczęcia zatrudnienia",
        "ro": "Data începerii angajării",
    },
    "Termination date": {
        "de": "Datum der Kündigung",
        "tr": "Fesih tarihi",
        "ar": "تاريخ إنهاء الخدمة",
        "uk": "Дата звільнення",
        "ru": "Дата увольнения",
        "pl": "Data wypowiedzenia",
        "ro": "Data concedierii",
    },
    "Contract type": {
        "de": "Vertragsart",
        "tr": "Sözleşme türü",
        "ar": "نوع العقد",
        "uk": "Тип договору",
        "ru": "Тип договора",
        "pl": "Rodzaj umowy",
        "ro": "Tipul contractului",
    },
    "Monthly salary": {
        "de": "Monatliches Gehalt",
        "tr": "Aylık maaş",
        "ar": "الراتب الشهري",
        "uk": "Місячна зарплата",
        "ru": "Ежемесячная зарплата",
        "pl": "Miesięczne wynagrodzenie",
        "ro": "Salariul lunar",
    },
    "Desired outcome": {
        "de": "Gewünschtes Ergebnis",
        "tr": "İstenen sonuç",
        "ar": "النتيجة المرجوة",
        "uk": "Бажаний результат",
        "ru": "Желаемый результат",
        "pl": "Oczekiwany rezultat",
        "ro": "Rezultatul dorit",
    },
    "Nationality": {
        "de": "Staatsangehörigkeit",
        "tr": "Uyruk",
        "ar": "الجنسية",
        "uk": "Громадянство",
        "ru": "Гражданство",
        "pl": "Narodowość",
        "ro": "Naționalitatea",
    },
    "Current residence status": {
        "de": "Aktueller Aufenthaltsstatus",
        "tr": "Mevcut oturum durumu",
        "ar": "حالة الإقامة الحالية",
        "uk": "Поточний статус проживання",
        "ru": "Текущий статус проживания",
        "pl": "Aktualny status pobytu",
        "ro": "Statutul actual de ședere",
    },
    "Permit/visa type": {
        "de": "Art der Aufenthaltserlaubnis/des Visums",
        "tr": "İzin/vize türü",
        "ar": "نوع التصريح/التأشيرة",
        "uk": "Тип дозволу/візи",
        "ru": "Тип разрешения/визы",
        "pl": "Rodzaj zezwolenia/wizy",
        "ro": "Tipul permisului/vizei",
    },
    "Relevant dates": {
        "de": "Relevante Daten",
        "tr": "İlgili tarihler",
        "ar": "التواريخ ذات الصلة",
        "uk": "Відповідні дати",
        "ru": "Соответствующие даты",
        "pl": "Istotne daty",
        "ro": "Date relevante",
    },
    "Tenant name": {
        "de": "Name des Mieters",
        "tr": "Kiracı adı",
        "ar": "اسم المستأجر",
        "uk": "Ім'я орендаря",
        "ru": "Имя арендатора",
        "pl": "Imię i nazwisko najemcy",
        "ro": "Numele chiriașului",
    },
    "Landlord name": {
        "de": "Name des Vermieters",
        "tr": "Ev sahibi adı",
        "ar": "اسم المالك",
        "uk": "Ім'я орендодавця",
        "ru": "Имя арендодателя",
        "pl": "Imię i nazwisko wynajmującego",
        "ro": "Numele proprietarului",
    },
    "Property address": {
        "de": "Adresse der Immobilie",
        "tr": "Mülkün adresi",
        "ar": "عنوان العقار",
        "uk": "Адреса об'єкта",
        "ru": "Адрес объекта",
        "pl": "Adres nieruchomości",
        "ro": "Adresa proprietății",
    },
    "Description of the defect": {
        "de": "Beschreibung des Mangels",
        "tr": "Ayıbın açıklaması",
        "ar": "وصف العيب",
        "uk": "Опис несправності",
        "ru": "Описание недостатка",
        "pl": "Opis usterki",
        "ro": "Descrierea defectului",
    },
    "Date defect was noticed": {
        "de": "Datum der Feststellung des Mangels",
        "tr": "Ayıbın fark edildiği tarih",
        "ar": "تاريخ ملاحظة العيب",
        "uk": "Дата виявлення несправності",
        "ru": "Дата обнаружения недостатка",
        "pl": "Data zauważenia usterki",
        "ro": "Data observării defectului",
    },
    "Requested remedy": {
        "de": "Gewünschte Abhilfe",
        "tr": "Talep edilen çözüm",
        "ar": "الإجراء التصحيحي المطلوب",
        "uk": "Бажане усунення",
        "ru": "Желаемое устранение",
        "pl": "Oczekiwane rozwiązanie",
        "ro": "Remediul solicitat",
    },
    "Company name": {
        "de": "Name des Unternehmens",
        "tr": "Şirket adı",
        "ar": "اسم الشركة",
        "uk": "Назва компанії",
        "ru": "Название компании",
        "pl": "Nazwa firmy",
        "ro": "Numele companiei",
    },
    "Order/invoice reference": {
        "de": "Bestell-/Rechnungsnummer",
        "tr": "Sipariş/fatura numarası",
        "ar": "رقم الطلب/الفاتورة",
        "uk": "Номер замовлення/рахунку",
        "ru": "Номер заказа/счета",
        "pl": "Numer zamówienia/faktury",
        "ro": "Numărul comenzii/facturii",
    },
    "Purchase date": {
        "de": "Kaufdatum",
        "tr": "Satın alma tarihi",
        "ar": "تاريخ الشراء",
        "uk": "Дата покупки",
        "ru": "Дата покупки",
        "pl": "Data zakupu",
        "ro": "Data achiziției",
    },
    "Description of the issue": {
        "de": "Beschreibung des Problems",
        "tr": "Sorunun açıklaması",
        "ar": "وصف المشكلة",
        "uk": "Опис проблеми",
        "ru": "Описание проблемы",
        "pl": "Opis problemu",
        "ro": "Descrierea problemei",
    },
}


def _t(text: str, lang: str) -> str:
    lang = normalize_language(lang)
    if lang == "en":
        return text
    return _TRANSLATIONS.get(text, {}).get(lang, text)


def translate_template(t: FormTemplate, lang: str) -> dict:
    """Render a template as a dict with title/description/labels translated
    into `lang`, falling back to English wherever a translation is missing."""
    return {
        "id": t.id,
        "category": t.category,
        "title": _t(t.title, lang),
        "description": _t(t.description, lang),
        "fields": [
            {"key": f.key, "label": _t(f.label, lang), "required": f.required}
            for f in t.fields
        ],
    }


def get_template(template_id: str) -> FormTemplate | None:
    return TEMPLATES.get(template_id)


def templates_for_category(category: str) -> list[FormTemplate]:
    return [t for t in TEMPLATES.values() if t.category.lower() == category.lower()]
