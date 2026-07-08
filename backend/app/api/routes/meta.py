"""Public metadata routes (no auth required)."""
from __future__ import annotations

from fastapi import APIRouter

from app.core.languages import LANGUAGE_NAMES

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/languages")
def list_languages() -> list[dict]:
    return [{"code": code, "name": name} for code, name in LANGUAGE_NAMES.items()]
