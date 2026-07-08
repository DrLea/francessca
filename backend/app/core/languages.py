"""Supported languages for multilingual conversation, exports, and forms.

Adding a language means: add it here, add its template-label translations in
`app.services.templates`, and (optionally) its export section-label
translations in `app.services.export_service`. Everything else (chat
responses, case-summary generation) works automatically because it is
produced live by the model based on the instruction in `language_instruction`.
"""
from __future__ import annotations

# code -> native display name (shown in language pickers)
LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "de": "Deutsch",
    "tr": "Türkçe",
    "ar": "العربية",
    "uk": "Українська",
    "ru": "Русский",
    "pl": "Polski",
    "ro": "Română",
}

# English name used inside AI instructions (the model follows these more
# reliably in English than in the native name).
_ENGLISH_NAME: dict[str, str] = {
    "en": "English",
    "de": "German",
    "tr": "Turkish",
    "ar": "Arabic",
    "uk": "Ukrainian",
    "ru": "Russian",
    "pl": "Polish",
    "ro": "Romanian",
}

SUPPORTED_LANGUAGES: list[str] = list(LANGUAGE_NAMES.keys())

DEFAULT_LANGUAGE = "en"


def normalize_language(code: str | None) -> str:
    """Fall back to the default for unknown/missing codes."""
    if not code:
        return DEFAULT_LANGUAGE
    code = code.lower().strip()
    return code if code in LANGUAGE_NAMES else DEFAULT_LANGUAGE


def language_instruction(code: str) -> str:
    """Appended to the mandatory system prompt so chat replies come back in
    the user's preferred language while keeping every other guardrail intact.
    """
    name = _ENGLISH_NAME.get(normalize_language(code), "English")
    return (
        f"\n\nThe user's preferred language is {name}. Always reply in {name}, "
        f"even if the user writes in a different language — unless they "
        f"explicitly ask you to switch languages."
    )


def document_language_instruction(code: str) -> str:
    """Used for generated documents (case summaries, exports) where the
    output should always match the user's preference, regardless of which
    language the underlying conversation happened in.
    """
    name = _ENGLISH_NAME.get(normalize_language(code), "English")
    return (
        f"\n\nWrite all generated text (titles, descriptions, list items, "
        f"narrative) in {name}. Keep any requested JSON keys in English "
        f"exactly as specified — only the string values should be in {name}."
    )
