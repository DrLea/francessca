"""AI-assisted extraction of calendar entries into a per-user case timeline.

This is deliberately NOT a chronology of everything that happened. It is a
diary: appointments, hearings, deadlines, expiry dates — entries that belong
to a specific day and that the user would otherwise have to keep track of
by hand ("31.08.2026 Ausländerbehörde", "12.12.2030 passport expires").

Narrative facts ("the user was dismissed", "employed for 1-5 years") are
deliberately excluded, however datable they look: they belong in the case
summary, not in a calendar. Three filters enforce that:

1. a chat message is only sent for extraction when it actually looks like it
   mentions a date or a scheduled thing (documents are always scanned);
2. the model must classify every entry as one of a fixed set of calendar
   kinds, and must resolve it to a real YYYY-MM-DD date;
3. anything that comes back without a valid date or a known kind is dropped
   server-side, so a chatty model cannot pollute the timeline.

Extraction is strictly best-effort:
- it reuses the mandatory Francessca system prompt, so the same "no legal
  advice / no predictions" guardrails apply to this call as to any other;
- it never invents facts — only entries actually stated in the text;
- it never raises. A failure (bad JSON, no budget left, network error) is
  logged and simply results in zero new events, so it can never break the
  upload or chat flow that triggers it.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.timeline_event import TimelineEvent, TimelineSourceType
from app.models.user import User
from app.repositories.timeline_repo import TimelineRepository
from app.services.ai_service import AIService, build_ai_service
from app.services.prompt_service import PromptService
from app.services.token_service import TokenService, estimate_tokens

log = get_logger("francessca.timeline")

# Skip trivially short text — not worth an AI call and unlikely to contain a
# datable fact.
_MIN_LENGTH = 20

# Sanity bounds for a resolved date: anything outside is a model slip.
_MIN_YEAR, _MAX_YEAR = 1990, 2100

# The only entry kinds allowed into the timeline. Anything else the model
# invents ("event", "fact", "termination") is dropped.
_DEADLINE_KINDS = {"deadline", "expiry", "payment", "submission"}
_APPOINTMENT_KINDS = {"appointment", "hearing", "meeting"}
_ALLOWED_KINDS = _DEADLINE_KINDS | _APPOINTMENT_KINDS

# Words that suggest a chat message is about scheduling. Used only to decide
# whether a message is worth an extraction call at all -- documents are
# always scanned. Any digit in the message also passes the gate, which is
# what catches "31.08.2026" and "on the 12th" in every language.
_SCHEDULE_HINTS: tuple[str, ...] = (
    # en
    "today", "tomorrow", "tonight", "next week", "next month", "appointment",
    "meeting", "deadline", "hearing", "expire", "expiry", "due", "schedul",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    # de
    "heute", "morgen", "übermorgen", "nächste", "termin", "besprechung",
    "frist", "anhörung", "läuft ab", "gültig", "montag", "dienstag",
    "mittwoch", "donnerstag", "freitag", "samstag", "sonntag",
    # tr
    "bugün", "yarın", "randevu", "toplantı", "son tarih", "duruşma",
    "süresi", "pazartesi", "salı", "çarşamba", "perşembe", "cuma", "pazar",
    # ar
    "اليوم", "غدا", "غدًا", "موعد", "اجتماع", "جلسة", "ينتهي", "الأسبوع القادم",
    # uk
    "сьогодні", "завтра", "післязавтра", "зустріч", "прийом", "термін",
    "дедлайн", "засідання", "закінчується", "понеділок", "вівторок",
    "середа", "четвер", "п'ятниця", "субота", "неділя",
    # ru
    "сегодня", "завтра", "послезавтра", "встреча", "приём", "прием", "срок",
    "дедлайн", "заседание", "истекает", "понедельник", "вторник", "среда",
    "четверг", "пятница", "суббота", "воскресенье",
    # pl
    "dziś", "dzisiaj", "jutro", "spotkanie", "termin", "rozprawa", "wygasa",
    "poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela",
    # ro
    "azi", "astăzi", "mâine", "întâlnire", "programare", "termen", "ședință",
    "expiră", "luni", "marți", "miercuri", "joi", "vineri", "sâmbătă", "duminică",
    # "put this in my timeline / calendar" — an explicit request must always
    # reach the model, whatever else the message contains.
    "timeline", "calendar", "diary", "remind",
    "zeitleiste", "kalender", "erinner",
    "takvim", "zaman çizelgesi", "hatırlat",
    "التقويم", "الجدول الزمني", "ذكرني",
    "хронологі", "календар", "нагада",
    "хронологи", "напомн",
    "oś czasu", "kalendarz", "przypomn",
    "cronologi", "amintește",
)

_DIGIT_RE = re.compile(r"\d")

_EXTRACTION_INSTRUCTION = """Extract ONLY calendar entries from the text below \
— things that belong in a diary because they happen, or must be done, on one \
specific day.

Include exactly these kinds:
- "appointment" — an appointment with an authority, office, doctor, lawyer or employer
- "hearing" — a court or tribunal hearing
- "meeting" — a scheduled meeting
- "deadline" — a time limit the user must act within (objection period, notice period, response due)
- "expiry" — the date a document, permit, visa, passport, contract or insurance stops being valid
- "payment" — a payment due on a specific day
- "submission" — something that must be filed or sent by a specific day

Do NOT include narrative facts about what happened or how long something \
lasted — a dismissal, an argument, a phone call, when a job started or ended, \
"for 1 to 5 years", "at termination". Those belong in the case summary, never \
in a calendar. When in doubt, leave it out.

Today is {today}. Resolve relative expressions ("tomorrow", "next Monday", \
"in two weeks") against that date.

Return a JSON array. Each item must have exactly these keys:
- "date": the resolved calendar date as "YYYY-MM-DD". REQUIRED — if you cannot \
pin the entry to one specific day, leave the entry out entirely.
- "kind": one of appointment, hearing, meeting, deadline, expiry, payment, submission
- "date_label": the date phrase exactly as written in the text (e.g. "tomorrow at 10:30", "31.08.2026")
- "description": one short factual sentence — what is scheduled, with whom or \
about what. No legal conclusions, no advice, no predictions.

Never invent a date or an entry. If the text contains no calendar entry, \
return an empty array [].
Output ONLY the JSON array. No prose, no code fences."""

_CONTEXT_PREFIX = """Earlier in the conversation (background only — use it to \
resolve what the user is referring to, for example when they say "add it to my \
timeline"):
"""


def looks_scheduling_related(text: str) -> bool:
    """Cheap pre-filter for chat messages.

    Most chat turns ("I was fired yesterday", "what should I do?") contain no
    calendar entry, and sending them all to the model both costs tokens and
    tempts it to invent entries. A message passes if it contains any digit or
    any scheduling word in one of the supported languages.
    """
    if _DIGIT_RE.search(text):
        return True
    lowered = text.lower()
    return any(hint in lowered for hint in _SCHEDULE_HINTS)


class TimelineService:
    def __init__(self, db: Session, ai: AIService | None = None) -> None:
        self.db = db
        self.events = TimelineRepository(db)
        self.prompts = PromptService(db)
        self.tokens = TokenService(db)
        self.ai = ai or build_ai_service()

    def list_for_user(self, user_id: int) -> list[TimelineEvent]:
        return self.events.list_for_user(user_id)

    def add_manual(
        self,
        user: User,
        *,
        event_date: date,
        description: str,
        is_deadline: bool = False,
    ) -> TimelineEvent:
        """An entry the user typed in themselves — no model involved."""
        event = TimelineEvent(
            user_id=user.id,
            event_date=event_date,
            date_label=event_date.isoformat(),
            description=description.strip()[:2000],
            is_deadline=is_deadline,
            source_type=TimelineSourceType.manual,
            source_id=None,
        )
        self.events.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def delete_for_user(self, event_id: int, user_id: int) -> bool:
        """Delete one event the user owns. Returns False if it isn't theirs."""
        event = self.events.get_for_user(event_id, user_id)
        if event is None:
            return False
        self.events.delete(event)
        self.db.commit()
        return True

    def extract_from_text(
        self,
        user: User,
        text: str | None,
        *,
        source_type: TimelineSourceType,
        source_id: int | None,
        conversation_id: int | None = None,
        context: str | None = None,
    ) -> list[TimelineEvent]:
        """Best-effort extraction. Flushes new rows but does not commit —
        the caller (chat/file service) owns the transaction boundary.

        `context` is the preceding turn, passed for chat messages only: it is
        what lets "add it to my timeline" refer back to the appointment that
        was just discussed. The gate below still looks only at `text`, so
        context never causes an extraction on its own.
        """
        text = (text or "").strip()
        if len(text) < _MIN_LENGTH:
            return []
        # Chat is noisy; only spend a call on messages that mention a date or
        # something scheduled. Documents are always worth scanning.
        if source_type is TimelineSourceType.message and not looks_scheduling_related(
            text
        ):
            return []

        try:
            estimated = estimate_tokens(text) + 300
            if not user.is_unlimited and estimated > (self.tokens.remaining(user) or 0):
                log.info("timeline extraction skipped: token budget exhausted")
                return []

            instruction = _EXTRACTION_INSTRUCTION.format(
                today=date.today().isoformat()
            )
            if context and context.strip():
                instruction = (
                    f"{instruction}\n\n{_CONTEXT_PREFIX}{context.strip()[:1500]}"
                )
            result = self.ai.complete(
                system_prompt=self.prompts.active_system_prompt(),
                messages=[
                    {
                        "role": "user",
                        "content": f"{instruction}\n\nText:\n{text}",
                    }
                ],
                max_tokens=800,
            )
            self.tokens.record(
                user,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                model=result.model,
                conversation_id=conversation_id,
            )
            items = self._parse(result.text)
        except Exception as exc:  # noqa: BLE001 - extraction must never break the caller
            log.warning("timeline extraction failed: %s", exc)
            return []

        created: list[TimelineEvent] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            description = str(item.get("description") or "").strip()[:2000]
            event_date = self._parse_date(item.get("date"))
            kind = str(item.get("kind") or "").strip().lower()
            # The three hard filters: a real day, a real calendar kind, and
            # something to show. Anything else is narrative, not a diary entry.
            if not description or event_date is None or kind not in _ALLOWED_KINDS:
                continue
            if self.events.exists_similar(user.id, event_date, description):
                continue
            event = TimelineEvent(
                user_id=user.id,
                conversation_id=conversation_id,
                event_date=event_date,
                date_label=str(item.get("date_label") or "")[:128],
                description=description,
                is_deadline=kind in _DEADLINE_KINDS,
                source_type=source_type,
                source_id=source_id,
            )
            self.events.add(event)
            created.append(event)
        return created

    @staticmethod
    def _parse(raw: str) -> list:
        """Parse the model's JSON array, tolerating code fences and stray prose."""
        text = raw.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        start, end = text.find("["), text.rfind("]")
        if start == -1 or end == -1:
            return []
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            log.warning("could not parse timeline extraction JSON")
            return []
        return data if isinstance(data, list) else []

    @staticmethod
    def _parse_date(value: object) -> date | None:
        if not value or not isinstance(value, str):
            return None
        try:
            parsed = datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
        if not _MIN_YEAR <= parsed.year <= _MAX_YEAR:
            return None
        return parsed
