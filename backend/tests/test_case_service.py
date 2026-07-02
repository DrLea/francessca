"""Tests for case-summary JSON parsing."""
from __future__ import annotations

from app.services.case_service import CaseService


def test_parse_summary_handles_code_fence():
    raw = """```json
    {"case_type": "Employment", "timeline": ["fired on 2026-06-29"],
     "questions_for_lawyer": ["Is the notice period correct?"]}
    ```"""
    summary = CaseService._parse_summary(raw, ["contract.pdf"])
    assert summary.case_type == "Employment"
    assert summary.timeline == ["fired on 2026-06-29"]
    assert summary.attachments == ["contract.pdf"]


def test_parse_summary_falls_back_to_narrative_on_bad_json():
    summary = CaseService._parse_summary("not json at all", [])
    assert "not json" in summary.narrative


def test_parse_summary_ignores_unknown_keys():
    summary = CaseService._parse_summary('{"case_type": "Tax", "bogus": 1}', [])
    assert summary.case_type == "Tax"
