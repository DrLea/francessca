"""Case and case-summary schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CaseSummary(BaseModel):
    """Structured case summary produced for a lawyer."""

    case_type: str = ""
    timeline: list[str] = Field(default_factory=list)
    people_involved: list[str] = Field(default_factory=list)
    important_dates: list[str] = Field(default_factory=list)
    documents_available: list[str] = Field(default_factory=list)
    missing_documents: list[str] = Field(default_factory=list)
    questions_for_lawyer: list[str] = Field(default_factory=list)
    potential_relevant_topics: list[str] = Field(default_factory=list)
    generated_forms: list[str] = Field(default_factory=list)
    attachments: list[str] = Field(default_factory=list)
    narrative: str = ""


class CaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    case_type: str | None
    summary: dict
    created_at: datetime
    updated_at: datetime


class CaseExportRequest(BaseModel):
    conversation_id: int
    title: str | None = None
    # If true, also build a ZIP including uploaded documents.
    include_documents: bool = True
