"""Lead quality score: how complete a case is when it reaches a lawyer.

Deliberately a plain heuristic over data the app already has — no model
call — so sending a case costs the client no tokens and the score is
reproducible. The breakdown is stored with the order so a lawyer (and the
admin, next to the lawyer's own feedback) can see *why* a lead scored as it
did.
"""
from __future__ import annotations

# (key, max points). Sums to 100.
WEIGHTS: tuple[tuple[str, int], ...] = (
    ("narrative", 20),
    ("timeline", 15),
    ("documents", 20),
    ("dates", 10),
    ("people", 10),
    ("questions", 10),
    ("case_type", 5),
    ("message", 10),
)


def _items(summary: dict, key: str) -> list:
    value = summary.get(key) or []
    return [v for v in value if v] if isinstance(value, list) else []


def _scaled(count: int, full_at: int, points: int) -> int:
    """`points` once `count` reaches `full_at`, proportionally less below."""
    if full_at <= 0:
        return 0
    return round(points * min(count, full_at) / full_at)


def score_lead(
    summary: dict | None,
    *,
    message: str | None = None,
    document_count: int = 0,
    timeline_count: int = 0,
) -> tuple[int, dict[str, int]]:
    """Return (score 0-100, per-criterion points)."""
    summary = summary or {}
    weights = dict(WEIGHTS)

    narrative = str(summary.get("narrative") or "").strip()
    documents = max(document_count, len(_items(summary, "documents_available")))
    timeline = max(timeline_count, len(_items(summary, "timeline")))

    breakdown = {
        # ~600 characters is a solid paragraph describing what happened.
        "narrative": _scaled(len(narrative), 600, weights["narrative"]),
        "timeline": _scaled(timeline, 4, weights["timeline"]),
        "documents": _scaled(documents, 3, weights["documents"]),
        "dates": _scaled(len(_items(summary, "important_dates")), 2, weights["dates"]),
        "people": _scaled(len(_items(summary, "people_involved")), 2, weights["people"]),
        "questions": _scaled(
            len(_items(summary, "questions_for_lawyer")), 2, weights["questions"]
        ),
        "case_type": weights["case_type"]
        if str(summary.get("case_type") or "").strip()
        else 0,
        "message": _scaled(len((message or "").strip()), 120, weights["message"]),
    }
    return min(100, sum(breakdown.values())), breakdown
