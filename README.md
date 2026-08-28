# Francessca

Francessca is **not** a legal consultation platform and does **not** give legal advice. It is an AI assistant that helps users prepare for speaking with a qualified lawyer: it asks clarifying questions, collects the facts chronologically, helps fill publicly-available forms, produces a structured case summary, recommends German lawyers, and lets users contact them.

Every AI request is prepended with a mandatory system prompt that forbids legal advice, predictions, or representation as a lawyer, and every generated document ends with a recommendation to have it reviewed by a qualified lawyer.

## Architecture

```
backend/    FastAPI + SQLAlchemy + Alembic + PostgreSQL + Redis
            JWT + Google OAuth, Anthropic Claude Haiku, repository/service pattern
frontend/   Next.js + React + TypeScript + TailwindCSS (minimal scaffold)
docker-compose.yml   db + redis + backend + frontend
```

Backend layout:

```
app/
  api/routes/   HTTP layer (auth, me, chat, files, lawyers, case, dashboard, admin)
  services/     business logic (auth, chat, ai, token, file, ocr, case, export, lawyer, prompt)
  repositories/ data access (repository pattern over SQLAlchemy)
  models/       ORM models
  schemas/      Pydantic request/response models
  scraper/      rak-muenchen.de directory scraper (cached, change-detecting)
  seeds/        sample lawyer dataset
  core/         security, logging, system prompt
```

## Requirements

- Docker and Docker Compose (recommended), or
- Python 3.12+, PostgreSQL 16, Redis 7, Node 20 for a local install.

## Environment

Copy the template and fill in real values. **No secrets are hardcoded** — everything comes from the environment.

```bash
cp .env.template .env
# then edit .env
```

Key variables: `DATABASE_URL`, `JWT_SECRET`, `REDIS_URL`, `ANTHROPIC_API_KEY`, `GOOGLE_CLIENT_ID/SECRET`, SMTP settings, `FRONTEND_URL`, `BACKEND_URL`, `FREE_TIER_TOKEN_LIMIT`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`.

Generate a strong JWT secret:

```bash
openssl rand -hex 32
```

## Running (one command)

```bash
docker compose up --build
```

This starts PostgreSQL, Redis, the backend (which runs migrations and bootstraps the admin + seed data on startup), and the frontend.

- API:        http://localhost:8000
- API docs:   http://localhost:8000/docs  (OpenAPI / Swagger)
- Frontend:   http://localhost:3000

## Running locally (without Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export $(grep -v '^#' ../.env | xargs)   # load env
alembic upgrade head
python -m app.bootstrap                  # admin + seed data
uvicorn app.main:app --reload
```

Tesseract is required for image OCR (`apt-get install tesseract-ocr tesseract-ocr-deu`). The Docker image installs it automatically.

## Migrations

```bash
cd backend
alembic upgrade head                      # apply
alembic revision --autogenerate -m "msg"  # create a new migration
alembic downgrade -1                       # roll back one
```

## Creating an admin

Set `ADMIN_EMAIL` and `ADMIN_PASSWORD` in `.env`; the admin is created automatically on startup by `app.bootstrap`. To create one manually:

```bash
cd backend
python -c "from app.bootstrap import run; run()"
```

An existing user can also be promoted via `PATCH /admin/users/{id}` with `{\"role\": \"admin\"}` by another admin.

## API documentation

Interactive OpenAPI docs are served at `/docs` and the raw schema at `/openapi.json`.

| Method | Path | Description |
| --- | --- | --- |
| POST | `/auth/register` | Register with email + password |
| POST | `/auth/login` | Log in |
| POST | `/auth/google` | Log in / sign up with a Google ID token |
| GET | `/me` | Current user profile |
| POST | `/me/plan` | Switch plan (free while in beta — no payment step) |
| GET | `/public/lawyers` | **No auth.** Contact-free directory preview for the landing page |
| POST | `/public/lawyer-applications` | **No auth.** A lawyer applies to be listed |
| GET | `/admin/lawyer-applications` | Review queue (admin) |
| POST | `/admin/lawyer-applications/{id}/approve` | Publish an application to the directory (admin) |
| POST | `/admin/lawyer-applications/{id}/reject` | Reject an application (admin) |
| POST | `/chat` | Send a message and/or a batch of answers to clarifying questions (creates conversation if needed) |
| GET | `/chat` | List conversations |
| GET | `/chat/{id}` | Conversation with full message history |
| POST | `/files` | Upload a document (PDF/image/DOCX/TXT, ≤25 MB; OCR on images) |
| GET | `/files` | List uploaded documents |
| GET | `/lawyers` | List lawyers |
| GET | `/lawyers/search` | Search by specialization / city / language |
| POST | `/case/export` | Generate case summary + PDF (and ZIP of documents) |
| GET | `/case/export/{id}/download` | Download an export |
| GET | `/case/timeline` | Auto-extracted calendar: appointments, deadlines, expiry dates |
| POST | `/case/timeline` | Add an entry by hand |
| DELETE | `/case/timeline/{id}` | Remove one timeline entry |
| GET | `/meta/languages` | Supported UI/chat languages |
| GET | `/dashboard` | Dashboard counts |
| GET | `/usage` | Token usage and remaining allowance |
| `/admin/*` | | User management, token limits, prompt versions, lawyer sync, AI usage (admin only) |

## Guided clarifying questions

Francessca's job is to ask the right questions, but a paragraph full of them gets one answer at best. So when the model needs facts it appends a machine-readable block to its reply instead of asking in prose (the protocol lives in `app/core/clarify.py` and is appended to the mandatory system prompt on every chat turn, alongside the language instruction):

```
<questions>
[{"question": "When were you dismissed?", "choices": ["This week", "Earlier"]}]
</questions>
```

- The backend strips the block before storing the reply and keeps the parsed questions in `messages.questions` (JSON, migration `0003`), so a reload or a reopened conversation still offers questions that were never answered. Malformed blocks are discarded rather than shown.
- Caps are enforced server-side: at most 5 questions, 2–5 choices each, deduplicated. Any "Other"/"Not sure" choice the model invents is dropped — the UI always adds its own free-text option.
- If a reply arrives with questions written as prose instead (`- Do you have it? (Yes / No)`), `parse_prose_questions` converts those lines into real questions and lifts them out of the text, so a model that ignores the protocol still produces the same UI. Chat replies get 2000 output tokens, since a truncated reply would cut the trailing block off.
- The frontend (`components/ClarifyPrompt.tsx`) asks them **one at a time**, with `Skip` (this question) and `Skip all`, and sends the whole batch back in a single `POST /chat` as `answers: [{question, answer}]` — `answer: null` means skipped.
- **The model is called exactly as often as before: once per user turn, never once per question.** The answers are composed server-side into one readable user message (visible in the transcript and in the case export), and an all-skipped batch tells the model to move on rather than re-ask.

## Landing page

`/` is a public page, not a redirect: hero with a still of the guided-question flow, how-it-works, a preview of the directory, desktop downloads, plans, and a sign-up form for lawyers. Everything on it works logged out.

- **Directory preview** comes from `GET /public/lawyers`, which returns name, firm, city, specializations and languages only — email, phone and address stay behind the login on `/lawyers`.
- **Desktop downloads** are read from `NEXT_PUBLIC_DOWNLOAD_WINDOWS` / `_MAC` / `_LINUX` at build time (passed through `docker-compose.yml` build args as `DOWNLOAD_*`). While they are empty the whole section is hidden rather than showing dead links.
- **Plans** are Free and Premium. `POST /me/plan` moves a user between them with no payment step — Francessca is in beta, so Premium simply lifts the monthly token limit. **Put a payment provider in front of that endpoint before charging anyone.**
- **Lawyer sign-up** posts to `POST /public/lawyer-applications` and is stored as `pending` in `lawyer_applications` (migration `0004`). Nothing submitted there is visible anywhere until an admin calls `/admin/lawyer-applications/{id}/approve`, which creates the directory entry with a `source_key` of `application:<id>` so a later scraper sync can never overwrite or delete it. Rejected applications are kept for the record and never published.

## Case timeline

The timeline is a **calendar, not a chronology**: it holds entries that belong to one specific day — `31.08.2026 appointment at the Ausländerbehörde`, `12.12.2030 passport expires` — and deliberately not narrative facts like "the user was dismissed" or "employed for 1–5 years", which belong in the case summary. Three filters in `app/services/timeline_service.py` enforce that:

1. **Chat is gated before it costs anything.** A chat message is only sent for extraction when it looks like it mentions a date or something scheduled (any digit, or a scheduling word in one of the eight supported languages). "I was fired yesterday" never reaches the model; "ahh tomorrow I have a meeting" does. Uploaded documents are always scanned.
2. **The model must classify and date every entry.** It gets today's date (so "tomorrow" and "next Monday" resolve to a real day) and must return `kind` — one of `appointment`, `hearing`, `meeting`, `deadline`, `expiry`, `payment`, `submission` — plus a `YYYY-MM-DD` date.
3. **Anything else is dropped server-side.** No valid date, or a kind outside that set, and the entry never reaches the database, so a chatty model cannot pollute the calendar. Identical entries (same day, same description) are not filed twice. `deadline`/`expiry`/`payment`/`submission` are flagged as deadlines in the UI.

A chat message is extracted together with the previous assistant turn as context, so "add it to my timeline" resolves to the appointment just discussed; words like *timeline*, *calendar* and *remind* (in all eight languages) always pass the gate. Anything the extractor misses can be added by hand from the timeline page (`POST /case/timeline`, `source_type: manual`).

Every entry keeps the document or conversation it came from (`source_type` + `source_id`/`conversation_id`); `GET /case/timeline` resolves that to a filename or conversation title, and the UI links straight through to `/files?doc=<id>` or `/chat?c=<id>`. Entries the user doesn't want are removable with `DELETE /case/timeline/{id}`.

Only dated entries are returned, which also hides rows left over from the earlier, looser extractor without a data migration. Extraction still reuses the mandatory Francessca system prompt (same no-advice guardrails), never invents dates, and never blocks the upload/chat flow — a parse failure, network error, or exhausted token budget is logged and yields zero entries. The timeline feeds case-summary generation (`CaseService`) and gets its own dated section in the exported PDF (`ExportService`). Each extraction is a real Claude call; for production it's worth moving to a background task so it doesn't add latency to the request path.

## Multilingual conversation, exports & forms

Users have a `language` preference (`GET/PATCH /me`, `GET /meta/languages` for the supported list: English, German, Turkish, Arabic, Ukrainian, Russian, Polish, Romanian). It drives three things:

- **Chat** (`app/core/languages.py::language_instruction`): appended to the system prompt so replies come back in the user's language regardless of which language they type in.
- **Case summaries & exports** (`document_language_instruction`): generated narrative/summary text is produced directly in the user's language; the PDF's section headers and disclaimer are translated (`export_service.py`).
- **Form templates** (`app/services/templates.py`): titles, descriptions, and field labels are translated; `GET /case/templates?lang=xx` returns the translated version, falling back to English for anything not yet covered.

These are first-pass translations aimed at making the product usable immediately in each language — they have **not** been reviewed by a native legal-domain speaker and should get that review before being relied on in production, especially the AR/UK/RU/PL/RO form and export text. Also note: the PDF export does not yet do Arabic bidi/reshaping, so Arabic text in the PDF will not render right-to-left correctly without adding an Arabic-aware font and `python-bidi`/`arabic-reshaper`.

## Token limits

Every user has a monthly token allowance (`token_limit`; free tier defaults to `FREE_TIER_TOKEN_LIMIT`, premium is unlimited). Each AI request estimates tokens up-front and is **rejected with HTTP 402** if it would exceed the remaining allowance; actual usage is reconciled from the model response and recorded in the `token_usage` ledger. Admins can change any user's tier and limit.

## Lawyer directory & scraper

Source: <https://www.rak-muenchen.de/anwaltsverzeichnis/>. The scraper (`app/scraper/rak_muenchen.py`) is polite (rate-limited, identifies itself), caches fetched pages in Redis, and computes a `content_hash` per profile so unchanged records are skipped on re-sync. Trigger a sync via `POST /admin/lawyers/sync` (`live=false` reseeds the bundled sample dataset; `live=true` runs the real crawl). A sample dataset is seeded on first startup so search works immediately.

## Security

- Anthropic API key is server-side only and never exposed to the frontend; all AI calls go through the backend.
- JWT auth on every protected route; bcrypt password hashing.
- Upload validation (type + size), random stored filenames (no path traversal), per-user directories.
- Rate limiting (slowapi) and CORS restricted to configured origins.
- Prompt-injection mitigation: the mandatory system prompt is passed via the API's dedicated `system` parameter and never mixed into user turns; uploaded/user content is clearly delimited as data.
- Structured logging of AI requests, token usage, auth events, errors, and lawyer sync.

## Tests

```bash
cd backend
pytest
```

Covers security/JWT, token limits, scraper parsing, case-summary parsing, and an end-to-end API flow (register → chat with a stubbed AI → lawyer search) on an in-memory SQLite database.

## Deployment

1. Provision managed PostgreSQL and Redis; set `DATABASE_URL` and `REDIS_URL`.
2. Set all secrets via the environment (never commit `.env`). Use a strong `JWT_SECRET`.
3. Build and push the backend/frontend images (`Dockerfile.backend`, `Dockerfile.frontend`).
4. Run `alembic upgrade head` (the container entrypoint does this automatically).
5. Put the API behind TLS and a reverse proxy; set `CORS_ORIGINS` to your frontend domain.
6. Schedule `POST /admin/lawyers/sync?live=true` (e.g. nightly) to keep the directory fresh.

## Extending later

The architecture is intentionally modular so you can add lawyer accounts, paid subscriptions, multilingual prompts (PromptVersion already supports versions), more form templates (`app/services/templates.py` is data-driven), and additional bar-association directories (add a sibling scraper and reuse `LawyerService`).

## Disclaimer

Francessca organizes information and helps prepare documents. It does not provide legal advice, does not predict outcomes, and is not a substitute for a qualified lawyer.
