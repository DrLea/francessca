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
| POST | `/chat` | Send a message (creates conversation if needed) |
| GET | `/chat` | List conversations |
| GET | `/chat/{id}` | Conversation with full message history |
| POST | `/files` | Upload a document (PDF/image/DOCX/TXT, ≤25 MB; OCR on images) |
| GET | `/files` | List uploaded documents |
| GET | `/lawyers` | List lawyers |
| GET | `/lawyers/search` | Search by specialization / city / language |
| POST | `/case/export` | Generate case summary + PDF (and ZIP of documents) |
| GET | `/case/export/{id}/download` | Download an export |
| GET | `/case/timeline` | Auto-extracted, chronological case timeline |
| GET | `/meta/languages` | Supported UI/chat languages |
| GET | `/dashboard` | Dashboard counts |
| GET | `/usage` | Token usage and remaining allowance |
| `/admin/*` | | User management, token limits, prompt versions, lawyer sync, AI usage (admin only) |

## Case timeline

Every uploaded document and chat message is passed through a best-effort AI extraction step (`app/services/timeline_service.py`) that pulls out concrete, dated facts (a termination, a notice, a deadline, a meeting) into a `timeline_events` table — a running chronology the user would otherwise have to assemble by hand. Extraction:

- reuses the mandatory Francessca system prompt, so the same no-advice/no-prediction guardrails apply;
- never invents dates — only events actually stated in the text;
- never blocks the upload/chat flow — a parsing failure, network error, or exhausted token budget is logged and simply yields zero new events.

`GET /case/timeline` returns the chronology (dated events first, undated ones last); it also feeds into case-summary generation (`CaseService`) and is rendered as a dedicated, dated section in the exported PDF (`ExportService`). Because each extraction is a real Claude call, it adds one extra AI request (and its token cost) per document upload and per chat message — for production this is worth moving to a background task/queue so it doesn't add latency to the request path; it currently runs synchronously.

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
