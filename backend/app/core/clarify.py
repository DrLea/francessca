"""Structured clarifying questions.

Francessca's whole job is asking the right questions, but asking them in
prose makes the user face a wall of them at once -- and most people answer
only the first. Instead the model appends a small machine-readable block to
its reply; the frontend turns that into a one-question-at-a-time flow and
sends every answer back in a SINGLE follow-up turn. The model is therefore
called exactly as often as before: once per user turn, never once per
question.

Wire format (appended at the very end of an assistant reply):

    <questions>
    [{"question": "When were you dismissed?", "choices": ["This week", "Earlier"]}]
    </questions>

The block is stripped from the text before it is stored or shown, and the
parsed questions ride along on the message instead.
"""
from __future__ import annotations

import json
import re

from app.core.logging import get_logger

log = get_logger("francessca.clarify")

MAX_QUESTIONS = 5
MIN_CHOICES = 2
MAX_CHOICES = 5
MAX_QUESTION_LEN = 300
MAX_CHOICE_LEN = 120

# Primary form: an explicitly delimited block.
_BLOCK_RE = re.compile(r"<questions>(.*?)</questions>", re.DOTALL | re.IGNORECASE)
# Fallback: a bare JSON array of question objects at the very end of the reply
# (some models drop the tags). Anchored to the end so it can never swallow a
# JSON snippet the user themselves is asking about mid-message.
_BARE_RE = re.compile(r"\[\s*\{[^{}]*\"question\"\s*:.*?\}\s*\]\s*$", re.DOTALL)

# Choice labels that duplicate the free-text option the app always appends.
_OTHER_LABELS = {
    "other", "other…", "other...", "something else", "none of these",
    "none of the above", "not sure", "prefer not to say", "i don't know",
}


CLARIFY_PROTOCOL = """

## MANDATORY: how to ask the user for information

You often need facts before you can help. NEVER ask for them in prose and
NEVER write answer options inside your sentences. Every question you ask
MUST go in a question block at the very end of your reply:

<questions>
[{"question": "When did this happen?", "choices": ["This week", "This month", "Longer ago"]}]
</questions>

Wrong (never do this):
  - Do you have your contract? (Yes / No / Not sure)
  - Which country were you employed in?

Right: write your explanation, then put both of those in one question block
as the last thing in the reply.

Rules for the block:
- At most 5 questions, each with between 2 and 5 choices.
- Ask only for what you actually need next; fewer, sharper questions are better.
- Write the questions and the choices in the user's language.
- Choices must be short, concrete and mutually exclusive.
- Never include an "Other", "Something else" or "Not sure" choice. The
  application always adds a free-text option itself.
- Never re-ask something the user has already answered.
- Nothing may follow the block — no closing sentence, no sign-off.
- Omit the block entirely when you are answering, summarising, or drafting
  and need nothing from the user.

The application asks these questions one at a time and sends every answer
back in a single message, so keep them independent of each other.
"""


def _tidy(text: str) -> str:
    """Collapse the blank gap left behind when lines are lifted out."""
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _clean_choice(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())[:MAX_CHOICE_LEN].strip()
    if not text or text.lower() in _OTHER_LABELS:
        return None
    return text


def _clean_question(raw: object) -> dict[str, object] | None:
    if not isinstance(raw, dict):
        return None
    question = raw.get("question")
    if not isinstance(question, str):
        return None
    question = " ".join(question.split())[:MAX_QUESTION_LEN].strip()
    if not question:
        return None

    choices: list[str] = []
    for item in raw.get("choices") or []:
        cleaned = _clean_choice(item)
        # Case-insensitive de-duplication, first spelling wins.
        if cleaned and cleaned.lower() not in {c.lower() for c in choices}:
            choices.append(cleaned)
        if len(choices) == MAX_CHOICES:
            break
    if len(choices) < MIN_CHOICES:
        # A question with no usable choices is still worth asking -- the app
        # renders it as a free-text prompt.
        choices = []
    return {"question": question, "choices": choices}


def parse_questions(text: str) -> tuple[str, list[dict[str, object]]]:
    """Split an assistant reply into (visible text, structured questions).

    Never raises: malformed or missing blocks simply yield no questions, and
    the reply is returned as-is minus any block markers.
    """
    if not text:
        return "", []

    payload: str | None = None
    match = _BLOCK_RE.search(text)
    if match:
        payload = match.group(1)
        body = text[: match.start()] + text[match.end() :]
    else:
        match = _BARE_RE.search(text)
        if not match:
            # No block at all — the model may have asked in prose.
            return parse_prose_questions(text)
        payload = match.group(0)
        body = text[: match.start()]

    body = _tidy(body)
    try:
        data = json.loads(payload.strip())
    except json.JSONDecodeError:
        log.warning("Discarded malformed question block")
        return parse_prose_questions(body)

    if not isinstance(data, list):
        return body, []

    questions: list[dict[str, object]] = []
    seen: set[str] = set()
    for raw in data:
        cleaned = _clean_question(raw)
        if not cleaned:
            continue
        key = str(cleaned["question"]).lower()
        if key in seen:
            continue
        seen.add(key)
        questions.append(cleaned)
        if len(questions) == MAX_QUESTIONS:
            break
    return body, questions


# --- fallback: questions the model wrote as prose ------------------------
# Even with the protocol above, a smaller model sometimes falls back to
# "- Do you have X? (Yes / No / Not sure)". Rather than lose the choices,
# those lines are converted into real questions and removed from the text.
_PROSE_QUESTION_RE = re.compile(
    r"^\s*(?:[-*\u2022]\s*|\d+[.)]\s*)?(?P<q>[^()]*\?)\s*(?:\((?P<opts>[^()]*/[^()]*)\))?\s*$"
)
_PROSE_OPTIONS_RE = re.compile(r"^\s*\((?P<opts>[^()]*/[^()]*)\)\s*$")


def parse_prose_questions(text: str) -> tuple[str, list[dict[str, object]]]:
    """Recover questions a model wrote inline instead of in a block.

    Only fires when at least one of them offers slash-separated options —
    an ordinary reply that happens to end in a question is left alone, so
    the user can just answer it by typing.
    """
    lines = text.split("\n")
    # Classify every line once: a question, a bare options line, or neither.
    kinds: list[tuple[str, object]] = []
    for line in lines:
        opts_only = _PROSE_OPTIONS_RE.match(line)
        if opts_only:
            kinds.append(("options", opts_only.group("opts")))
            continue
        q = _PROSE_QUESTION_RE.match(line)
        if q and q.group("q").strip():
            kinds.append(("question", (q.group("q").strip(), q.group("opts"))))
            continue
        kinds.append(("text", None))

    # Take the longest contiguous run of question/options lines that contains
    # at least one set of options.
    best: tuple[int, int] | None = None
    i = 0
    while i < len(kinds):
        if kinds[i][0] == "question":
            j = i
            has_options = False
            while j < len(kinds) and kinds[j][0] in ("question", "options"):
                if kinds[j][0] == "options" or (kinds[j][1] and kinds[j][1][1]):  # type: ignore[index]
                    has_options = True
                j += 1
            if has_options and (best is None or (j - i) > (best[1] - best[0])):
                best = (i, j)
            i = j
        else:
            i += 1
    if best is None:
        return text.strip(), []

    start, end = best
    questions: list[dict[str, object]] = []
    for idx in range(start, end):
        kind, value = kinds[idx]
        if kind != "question":
            continue
        question, inline_opts = value  # type: ignore[misc]
        raw_opts = inline_opts
        if not raw_opts and idx + 1 < end and kinds[idx + 1][0] == "options":
            raw_opts = kinds[idx + 1][1]
        choices = [c.strip() for c in str(raw_opts or "").split("/")]
        cleaned = _clean_question({"question": question, "choices": choices})
        if cleaned:
            questions.append(cleaned)
        if len(questions) == MAX_QUESTIONS:
            break

    if not questions:
        return text.strip(), []
    body = "\n".join(lines[:start] + lines[end:])
    return _tidy(body), questions


def render_questions_for_history(questions: list[dict[str, object]]) -> str:
    """Compact plain-text rendering of an earlier question block.

    Stored assistant messages keep the questions in a separate column, so
    when the conversation is replayed to the model we re-attach them here --
    otherwise the model sees its own turn as if it had asked nothing.
    """
    lines: list[str] = []
    for q in questions:
        choices = [str(c) for c in (q.get("choices") or [])]
        suffix = f" ({' / '.join(choices)})" if choices else ""
        lines.append(f"- {q.get('question')}{suffix}")
    return "\n".join(lines)
