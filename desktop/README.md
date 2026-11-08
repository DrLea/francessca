# Francesca — offline desktop build

The same application as the server deployment, packaged as a single
executable that runs entirely on the user's machine:

```
Francesca.exe
  ├── llama.cpp server   127.0.0.1:8757   local model, no network
  └── FastAPI + uvicorn  127.0.0.1:8756   API *and* the exported UI
```

No Docker, no Postgres, no Node, no API key — and no request ever leaves the
machine. SQLite replaces Postgres, a bundled GGUF model replaces the
Anthropic API, and FastAPI serves the statically exported Next.js UI itself.

## What is where

| | |
|---|---|
| Bundled, read-only (inside the executable) | `frontend/` exported UI · `llama/` model server · `tesseract/` OCR engine |
| Per-user, writable | `%LOCALAPPDATA%\Francesca` (Windows) · `~/.local/share/Francesca` (Linux) · `~/Library/Application Support/Francesca` (macOS) |
| Kept there | `francessca.db`, `uploads/`, the downloaded `.gguf`, `secret.key` |

Upgrading is replacing the executable; the user's data stays put.

## Building it

**PyInstaller does not cross-compile.** A Windows `.exe` must be built on
Windows, a Linux binary on Linux.

### Windows

Needs Node 20+ on PATH, a Python, and (for image OCR)
[Tesseract](https://github.com/UB-Mannheim/tesseract/wiki).

**Which Python:** the script picks one itself through the `py` launcher,
preferring 3.12, then 3.13, then 3.11, and falling back to whatever `python`
resolves to. Newest is not best here — PyInstaller and the compiled
dependencies (pydantic-core, pillow, lxml) need wheels published for that
exact version, and a just-released Python often has none, so pip tries to
compile from source and fails without a C toolchain. If the build stops
there, install Python 3.12 from python.org, delete `desktop\.venv`, and run
it again; the launcher will pick 3.12 up automatically.

**Tesseract** is taken from `C:\Program Files\Tesseract-OCR` or from PATH,
whichever exists. The build keeps only the `deu`, `eng` and `osd` language
packs (the full set is ~1 GB) and warns if German or English is missing —
`tesseract --list-langs` should list both.

In **PowerShell** — note this is the `desktop` folder *inside* the project,
not your Windows Desktop:

```powershell
cd $HOME\Desktop\francessca\desktop
.\build.ps1
```

In **cmd.exe** (or by double-clicking it), use the wrapper instead — `.ps1`
files are not runnable from cmd:

```bat
cd %USERPROFILE%\Desktop\francessca\desktop
build.cmd
```

The script resolves the newest llama.cpp Windows CPU build from the releases
API by itself. Pass `-LlamaZipUrl "<url>"` only to pin a version or to use a
GPU build (cuda / vulkan / hip). If neither works, the build still succeeds —
the app then expects an OpenAI-compatible server (Ollama, LM Studio) on port
8757 instead of starting its own.

Result: `desktop\dist\Francesca.exe`.

First build takes a few minutes: it exports the UI, downloads llama.cpp,
copies Tesseract, creates a Python venv and installs the build
dependencies (`desktop/requirements-desktop.txt` — lower bounds rather than
the server's exact pins, so pip can resolve wheels for whichever Python you
build with). Later builds reuse all of that; add `-SkipFrontend` to skip the
UI export as well.

### macOS and Linux, without owning either

`.github/workflows/desktop.yml` builds all four targets on GitHub's runners
(Windows, macOS arm64, macOS x64, Linux x64) -- free for a public repo, and
the only practical answer since PyInstaller cannot cross-compile.

```bash
git tag v0.1.1 && git push origin v0.1.1
```

Each runner exports the UI, fetches the matching llama.cpp build, packages
with PyInstaller, writes a `.sha256` next to the binary and attaches both to
the release. The Actions tab's "Run workflow" button does the same without
tagging, leaving the binaries as downloadable artifacts for 14 days.

If a llama.cpp asset is missing for a platform, that step is skipped rather
than failing the build: the app then falls back to Ollama or any other
OpenAI-compatible server.

**Tesseract is not bundled on macOS or Linux** -- shared-library paths make
that fragile. The app finds a system install on PATH instead:

```bash
brew install tesseract tesseract-lang                    # macOS
sudo apt install tesseract-ocr tesseract-ocr-deu         # Debian/Ubuntu
```

Without it, everything works except OCR of scanned images.

**Gatekeeper.** An unsigned macOS binary is quarantined: users must
right-click and choose Open the first time, or run
`xattr -d com.apple.quarantine Francesca-macos-arm64`. Removing that means
notarizing with an Apple Developer account (99 USD/year) -- the same class
of problem as SmartScreen on Windows.

### Building locally on Linux / macOS

```bash
cd desktop
LLAMA_ZIP_URL=... ./build.sh     # or install llama-server on PATH first
```

## First run

1. Creates the app-data directory and a per-installation JWT secret.
2. Downloads the model (~2 GB) — once, with progress in the console. Set
   `FRANCESSCA_MODEL_URL` / `FRANCESSCA_MODEL_FILE` to use a different GGUF,
   or drop the file into the app-data directory beforehand to skip it.
3. Starts llama.cpp, creates the SQLite schema, seeds the sample lawyer
   directory, opens `http://127.0.0.1:8756/`.

Closing the console window stops both processes.

## Using Ollama instead of the bundled model

If Ollama is already running, the launcher finds it on port 11434 and uses it
instead of starting its own server or downloading a GGUF -- the app only needs
*an* OpenAI-compatible endpoint. It prefers a `qwen2.5` tag if you have one,
otherwise the first model Ollama lists. Force a specific one with
`FRANCESSCA_OLLAMA_MODEL=qwen2.5:7b`, or point anywhere at all with
`LOCAL_AI_BASE_URL` / `LOCAL_AI_MODEL`, which override everything.

For the **server** build, put the same thing in `.env`; from inside Docker,
`localhost` is the container, so use the host gateway:

```
AI_PROVIDER=local
LOCAL_AI_BASE_URL=http://host.docker.internal:11434/v1
LOCAL_AI_MODEL=qwen2.5:7b
```

### Ollama's context window

Ollama serves **4096 tokens of context by default**, and the system prompt,
the conversation and any attached document all share it -- whatever is left
is the room the model has to answer in. Overrun it and replies come back two
tokens long. The app keeps its prompts inside that budget
(`context_char_budget` in `ai_service.py`, ~6000 characters for local
models), but giving Ollama more room is worth it:

```
setx OLLAMA_CONTEXT_LENGTH 8192
```

then restart Ollama. Document translation is split into paragraph-sized
calls regardless, so it never depends on a large window.

## Model choice

The default is Qwen2.5-3B-Instruct (Q4_K_M): small enough to answer on a
CPU-only laptop, capable enough to follow the guided-question protocol.
`qwen2.5:7b` is the better pick wherever there is RAM for it.

Avoid reasoning models (Qwen3, DeepSeek-R1) if you can: they spend tokens --
and on a CPU, real seconds -- thinking before every answer. `LocalAIService`
strips their `<think>` blocks so they work, but they are slower for no gain
here.
Any GGUF chat model works — a 7B/8B at Q4 is noticeably better if the
machine has the RAM. Expect slower replies than the hosted build, and expect
the model to sometimes ask questions in prose rather than in the structured
block; the prose fallback in `app/core/clarify.py` recovers most of those.

## Differences from the server build

| | Server | Desktop |
|---|---|---|
| Database | Postgres + Alembic | SQLite, schema created from the models |
| Model | Anthropic API | bundled llama.cpp, local GGUF |
| Frontend | Next.js server (Node) | static export served by FastAPI |
| Lawyer directory | live scraper + Redis cache | bundled sample data |
| Google sign-in | available | unused (no network) |

The launcher sets `AI_PROVIDER=local`; everything else in the codebase is
shared, so a fix in the chat, timeline or export code lands in both builds.

## Publishing the download

The landing page asks the API for the list (`GET /public/downloads`), so a
release is a config change and a backend restart -- the frontend is not
rebuilt, and nothing is hardcoded in the bundle.

**1. Host the file.** Two options.

*From your own deployment (recommended).* Copy the build into `downloads/`
next to `docker-compose.yml` and set `DOWNLOAD_DIR=/data/downloads`:

```
francessca/downloads/Francesca.exe      # Windows
francessca/downloads/Francesca.dmg      # macOS
francessca/downloads/Francesca          # Linux
```

The API serves them at `/public/download/<platform>` on the app's own
domain, and computes the SHA-256 itself. This is reachable wherever the app
is -- GitHub's asset CDN (`release-assets.githubusercontent.com`) is not, on
some networks.

*From GitHub Releases.* Attach the file to a release and set
`DOWNLOAD_WINDOWS` to the asset URL. Less traffic through your server, but
it depends on a host your visitors may not be able to reach. A local file
wins over an external URL when both are configured.

**2. Take the checksums.** Only needed for the external route -- self-hosted
builds are hashed automatically:

```powershell
certutil -hashfile desktop\dist\Francesca.exe SHA256
```

**3. Point the deployment at it** in the root `.env`:

```
DOWNLOAD_VERSION=0.1.0
DOWNLOAD_DIR=/data/downloads
```

**4. Restart the backend:** `docker compose restart backend`. The download
section appears on the landing page with the version and the checksums under
the buttons. Clearing the variables hides it again.

### Before real users download it

Windows SmartScreen will warn on an unsigned executable, and some browsers
will discourage the download outright. An Authenticode certificate (roughly
€200-400/year from a CA, or an EV certificate for immediate reputation) is
what removes that. Until then, expect to explain the warning on the page --
and never ask people to disable SmartScreen.
