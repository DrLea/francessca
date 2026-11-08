# Francesca

Francesca is **not** a legal consultation platform and does **not** give legal advice. It is an AI assistant that helps users prepare for speaking with a qualified lawyer: it asks clarifying questions, collects the facts chronologically, helps fill publicly-available forms, produces a structured case summary, recommends German lawyers, and lets users contact them.

Every AI request is prepended with a mandatory system prompt that forbids legal advice, predictions, or representation as a lawyer, and every generated document ends with a recommendation to have it reviewed by a qualified lawyer.

## Architecture

```
backend/    FastAPI + SQLAlchemy + Alembic + PostgreSQL + Redis
            JWT + Google OAuth, self-hosted LLM (OpenAI-compatible; Claude optional),
            AES-256-GCM at rest, repository/service pattern
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

Key variables: `DATABASE_URL`, `JWT_SECRET`, `DATA_ENCRYPTION_KEY`, `REDIS_URL`, `AI_PROVIDER` + `LOCAL_AI_BASE_URL`/`LOCAL_AI_MODEL` (self-hosted model; `ANTHROPIC_API_KEY` only if you opt in), `GOOGLE_CLIENT_ID/SECRET`, SMTP settings, `FRONTEND_URL`, `BACKEND_URL`, `FAIR_USE_DAILY_TOKENS`, `LAWYER_TRIAL_MONTHS`, `LAWYER_MONTHLY_FEE`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`.

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
| POST | `/me/consent` | Consent to storing case data on our servers in Germany |
| GET | `/me/export` | **All** of the account's data as a ZIP (GDPR Art. 15/20) |
| DELETE | `/me` | Delete the account and every file on disk |
| GET | `/case/timeline/upcoming` | In-app reminders: dated entries in the next N days |
| POST | `/case/reply-draft` | Polite, firm German letter + translation, photos as evidence |
| POST | `/case/reply-draft/pdf` | That letter as a PDF, photos attached as *Anlagen* |
| POST | `/orders/{id}/withdraw` | Take back consent for a case already shared |
| POST | `/reports` | Report a lawyer (auto-suspends at `REPORT_SUSPEND_THRESHOLD`) |
| POST | `/lawyer/verification/bea` | Lawyer types back the code sent to their beA mailbox |
| GET | `/public/lawyers` | **No auth.** Contact-free directory preview for the landing page |
| GET | `/public/downloads` | **No auth.** Desktop builds on offer, from `DOWNLOAD_*` env |
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

Francesca's job is to ask the right questions, but a paragraph full of them gets one answer at best. So when the model needs facts it appends a machine-readable block to its reply instead of asking in prose (the protocol lives in `app/core/clarify.py` and is appended to the mandatory system prompt on every chat turn, alongside the language instruction):

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

## Offline desktop build

`desktop/` packages the whole application as a single executable that runs
with no network at all: SQLite instead of Postgres, a bundled llama.cpp
serving a local GGUF model instead of the Anthropic API, and the statically
exported frontend served by FastAPI itself — one process, one port.

```
Francesca.exe
  ├── llama.cpp server   127.0.0.1:8757
  └── FastAPI + uvicorn  127.0.0.1:8756   API and UI
```

The only switch in the shared code is `AI_PROVIDER=local`, which swaps
`AIService` (Anthropic) for `LocalAIService` (OpenAI-compatible); everything
else — chat, questions, timeline, exports — is the same code in both builds.
PyInstaller does not cross-compile, so each binary is built on its own OS:
locally with `desktop/build.ps1` (Windows) or `desktop/build.sh` (Linux and
macOS), or for all four targets at once by pushing a `v*` tag, which runs
`.github/workflows/desktop.yml` on GitHub's Windows, macOS and Linux runners
and attaches the binaries and their checksums to the release.
See `desktop/README.md` for prerequisites, the model choice, and how to
publish the result through the landing page's `DOWNLOAD_*` variables.

## Landing page

`/` is a public page, not a redirect: hero with a still of the guided-question flow, how-it-works, a preview of the directory, desktop downloads, plans, and a sign-up form for lawyers. Everything on it works logged out.

- **Directory preview** comes from `GET /public/lawyers`, which returns name, firm, city, specializations and languages only — email, phone and address stay behind the login on `/lawyers`.
- **Desktop downloads** come from `GET /public/downloads`, which reads the `DOWNLOAD_*` variables at request time — publishing a release is an `.env` change plus a backend restart, with no frontend rebuild. Checksums are shown under the buttons when set, since the executables are unsigned. While the variables are empty the whole section is hidden rather than showing dead links.
- **Pricing** follows the pitch deck: free for people (forever, no plans), law firms €99/month flat after 3 free months, universities and Law Clinics €500/month partner licence, white label later. Flat fees only, never per client (§49b Abs. 3 BRAO).
- **Trust** section: verified lawyers, data that stays in Germany, on-device mode.
- **Lawyer sign-up** posts to `POST /public/lawyer-applications` and is stored as `pending` in `lawyer_applications` (migration `0004`). Nothing submitted there is visible anywhere until an admin calls `/admin/lawyer-applications/{id}/approve`, which creates the directory entry with a `source_key` of `application:<id>` so a later scraper sync can never overwrite or delete it. Rejected applications are kept for the record and never published.

## Case timeline

The timeline is a **calendar, not a chronology**: it holds entries that belong to one specific day — `31.08.2026 appointment at the Ausländerbehörde`, `12.12.2030 passport expires` — and deliberately not narrative facts like "the user was dismissed" or "employed for 1–5 years", which belong in the case summary. Three filters in `app/services/timeline_service.py` enforce that:

1. **Chat is gated before it costs anything.** A chat message is only sent for extraction when it looks like it mentions a date or something scheduled (any digit, or a scheduling word in one of the eight supported languages). "I was fired yesterday" never reaches the model; "ahh tomorrow I have a meeting" does. Uploaded documents are always scanned.
2. **The model must classify and date every entry.** It gets today's date (so "tomorrow" and "next Monday" resolve to a real day) and must return `kind` — one of `appointment`, `hearing`, `meeting`, `deadline`, `expiry`, `payment`, `submission` — plus a `YYYY-MM-DD` date.
3. **Anything else is dropped server-side.** No valid date, or a kind outside that set, and the entry never reaches the database, so a chatty model cannot pollute the calendar. Identical entries (same day, same description) are not filed twice. `deadline`/`expiry`/`payment`/`submission` are flagged as deadlines in the UI.

A chat message is extracted together with the previous assistant turn as context, so "add it to my timeline" resolves to the appointment just discussed; words like *timeline*, *calendar* and *remind* (in all eight languages) always pass the gate. Anything the extractor misses can be added by hand from the timeline page (`POST /case/timeline`, `source_type: manual`).

Every entry keeps the document or conversation it came from (`source_type` + `source_id`/`conversation_id`); `GET /case/timeline` resolves that to a filename or conversation title, and the UI links straight through to `/files?doc=<id>` or `/chat?c=<id>`. Entries the user doesn't want are removable with `DELETE /case/timeline/{id}`.

Only dated entries are returned, which also hides rows left over from the earlier, looser extractor without a data migration. Extraction still reuses the mandatory Francesca system prompt (same no-advice guardrails), never invents dates, and never blocks the upload/chat flow — a parse failure, network error, or exhausted token budget is logged and yields zero entries. The timeline feeds case-summary generation (`CaseService`) and gets its own dated section in the exported PDF (`ExportService`). Each extraction is a real Claude call; for production it's worth moving to a background task so it doesn't add latency to the request path.

## Multilingual conversation, exports & forms

Users have a `language` preference (`GET/PATCH /me`, `GET /meta/languages` for the supported list: English, German, Turkish, Arabic, Ukrainian, Russian, Polish, Romanian). It drives three things:

- **Chat** (`app/core/languages.py::language_instruction`): appended to the system prompt so replies come back in the user's language regardless of which language they type in.
- **Case summaries & exports** (`document_language_instruction`): generated narrative/summary text is produced directly in the user's language; the PDF's section headers and disclaimer are translated (`export_service.py`).
- **Form templates** (`app/services/templates.py`): titles, descriptions, and field labels are translated; `GET /case/templates?lang=xx` returns the translated version, falling back to English for anything not yet covered.

These are first-pass translations aimed at making the product usable immediately in each language — they have **not** been reviewed by a native legal-domain speaker and should get that review before being relied on in production, especially the AR/UK/RU/PL/RO form and export text. Also note: the PDF export does not yet do Arabic bidi/reshaping, so Arabic text in the PDF will not render right-to-left correctly without adding an Arabic-aware font and `python-bidi`/`arabic-reshaper`.

## Fair use (no plans)

Francesca is free for people, so there is nothing to buy. The only limit is a hidden anti-abuse cap: a rolling 24-hour token budget per user (`FAIR_USE_DAILY_TOKENS`, default 200k), computed from the `token_usage` ledger. A request that would exceed it gets **HTTP 429** ("continue in a few hours"). Admins can override the cap per user (`token_limit`) or lift it (`tier = premium`, kept for staff and pilots, never sold). The UI shows no allowance.

## Lawyer directory & scraper

Source: <https://www.rak-muenchen.de/anwaltsverzeichnis/>. The scraper (`app/scraper/rak_muenchen.py`) is polite (rate-limited, identifies itself), caches fetched pages in Redis, and computes a `content_hash` per profile so unchanged records are skipped on re-sync. Trigger a sync via `POST /admin/lawyers/sync` (`live=false` reseeds the bundled sample dataset; `live=true` runs the real crawl). A sample dataset is seeded on first startup so search works immediately.

## Lawyer portal, orders & admin

Lawyers and clients sign in through separate doors and get separate sides of the app.

- **Lawyers** register at `/lawyer/register` (name, email, password, city) and can sign in at once (`/lawyer/login`). The profile stays out of the directory until an admin approves it. The portal at `/lawyer` has orders, closed deals, statistics, finance, a detailed profile editor and a feedback button.
- **Orders**: a client opens `/lawyers`, picks a lawyer who has an account and sends a prepared case (`POST /orders`). The lawyer sees the summary and a lead quality score (0-100, a heuristic in `services/lead_quality.py`, no model call); the client's name and email are revealed only on accept. Clients follow their requests at `/requests` and can rate the lawyer once the order is closed.
- **Subscription, never per client**: approval starts a free trial (`LAWYER_TRIAL_MONTHS`, default 3). After it a firm needs an active subscription (`LAWYER_MONTHLY_FEE`, default €99) to accept cases; leads themselves cost nothing. No payment provider is wired in: an admin records payment under `/admin/lawyers` ("+1 month"), which moves `paid_until` forward. Firms approved before migration `0006` got a fresh 3-month trial.
- **Per-case consent**: a case reaches a lawyer only after the client ticks consent for exactly that lawyer (`consent_at`). The client can take it back any time (`POST /orders/{id}/withdraw`); the lawyer then keeps the record but loses the case file and the client's contact.
- **Verification** (`services/verification_service.py`): (1) the lawyer enters their register entry, chamber and admission date, an admin checks them in the official BRAK register; (2) the admin issues a one-time code (only its hash is stored) and sends it to the lawyer's **beA** mailbox, the lawyer types it back; (3) ID check by video ident — no provider integrated yet, the admin records the result; (4) when all pass, the profile is verified for a year (`verified_until`), shown as a "Verified" badge; `/admin/rechecks-due` lists the ones expiring.
- **Reports & suspension**: clients can report a lawyer from `/requests`. `REPORT_SUSPEND_THRESHOLD` (default 3) open reports from different people suspend the lawyer at once; admins can suspend or lift instantly. A suspended lawyer is hidden from the directory and cannot receive cases.
- **Partners**: universities, Law Clinics and international offices hold a partner licence (`PARTNER_MONTHLY_FEE`, default €500), managed at `/admin/partners`; lawyer-portal accounts (e.g. supervised Law Clinic members) can be linked to a partner.
- **Admin** (`/admin`, admin accounts only): overview, lawyer approvals, subscriptions and verification (`/admin/lawyers`), reports (`/admin/reports`), partners (`/admin/partners`), and lawyer feedback (`/admin/feedback`).
- **Email**: sign-ups, approvals, new orders, responses and feedback are mailed when `SMTP_HOST` is set; otherwise they are only logged.

Migrations `0005_lawyer_portal` and `0006_deck_alignment` add all of this: run `alembic upgrade head`.

## Privacy: consent, encryption, export, delete

- **Consent before storing**: chat, uploads, case exports, reply letters and sending a case all require the user's consent to keep case data on our servers in Germany (`users.data_consent_at`, asked at sign-up or in a dialog — the API answers `428 consent_required`). Without it the offline app is the way to use Francesca. The desktop build sets `DATA_ON_DEVICE=true`, where none of this applies.
- **Encrypted at rest** (`app/core/crypto.py`): AES-256-GCM for uploaded files, exports, chat messages, extracted document text, timeline entries and case summaries. Set `DATA_ENCRYPTION_KEY` and **back it up**. Data written before this change stays readable and is encrypted when next written.
- **One tap**: `GET /me/export` returns everything as a ZIP; `DELETE /me` removes the account, cascades every row and deletes the files on disk. Both are on the dashboard.
- **Never used for training**, and with the default `AI_PROVIDER=local` no case data goes to a third-party AI service.

## Deadline reminders & German reply letters

- Every dated timeline entry is reminded **7 days and 1 day before**: by email (when `SMTP_HOST` is set) and in the app (dashboard "Coming up"). An hourly loop in the API process sends them; each goes once (`reminded_7d_at`, `reminded_1d_at`). `POST /admin/reminders/run` triggers it by hand.
- `/letters`: the user describes the problem in their language; Francesca writes a polite, firm German letter (facts and requests only, placeholders instead of invented details) plus a translation, in **one** model call. The user edits it and downloads a PDF with their photos attached as *Anlagen*.
- Arabic case-summary PDFs are reshaped and laid out right to left (`arabic-reshaper`, `python-bidi`).

## Installable app & offline assistant

The frontend is a PWA (`public/manifest.webmanifest`, `public/sw.js`, production builds only): on a phone it installs to the home screen, on a computer as a windowed desktop app. `/offline` runs a small model in the browser through WebLLM/WebGPU (`@mlc-ai/web-llm` — run `npm install` after pulling). The weights (about 400 MB or 1 GB) download once from the WebLLM model host and are cached by the browser; chats there stay in the browser's local storage until the user sends them to their account.

## Security

- Self-hosted models by default (`AI_PROVIDER=local`); the Anthropic key, if you opt in, is server-side only. All AI calls go through the backend.
- Case data encrypted at rest with AES-256-GCM; stored only with consent; per-case consent before a lawyer sees anything.
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

Still to wire in for production: a payment provider for law-firm subscriptions and partner licences (today an admin records payments), a video-ident provider for the ID check, and white label (year 2 in the deck). The architecture is intentionally modular so you can add multilingual prompts (PromptVersion already supports versions), more form templates (`app/services/templates.py` is data-driven), and additional bar-association directories (add a sibling scraper and reuse `LawyerService`).

## Disclaimer

Francesca organizes information and helps prepare documents. It does not provide legal advice, does not predict outcomes, and is not a substitute for a qualified lawyer.
