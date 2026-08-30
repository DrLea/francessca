"""Francessca desktop launcher.

One process, one port, nothing leaves the machine:

    [ this launcher ]
        ├── llama.cpp server   127.0.0.1:8757   (bundled binary + local GGUF)
        └── FastAPI + uvicorn  127.0.0.1:8756   (API *and* the exported UI)

Everything the packaged build needs that is not code lives next to the
executable (PyInstaller unpacks it to sys._MEIPASS):

    frontend/    the statically exported Next.js UI
    llama/       llama-server binary and its libraries
    tesseract/   optional, bundled OCR engine

Everything the *user* accumulates — the SQLite database, uploads, the
downloaded model — lives in their own app-data directory, so an upgrade is
just replacing the executable.
"""
from __future__ import annotations

import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

APP_NAME = "Francessca"
API_HOST = "127.0.0.1"
API_PORT = int(os.environ.get("FRANCESSCA_PORT", "8756"))
LLAMA_PORT = int(os.environ.get("FRANCESSCA_LLAMA_PORT", "8757"))
OLLAMA_PORT = int(os.environ.get("FRANCESSCA_OLLAMA_PORT", "11434"))

# If Ollama is already serving these, use them rather than starting a second
# model server. Qwen2.5 first: strong multilingual instruction-following and,
# unlike the Qwen3 line, no thinking mode to strip.
PREFERRED_OLLAMA_MODELS = (
    "qwen2.5:7b", "qwen2.5:7b-instruct", "qwen2.5:14b", "qwen2.5:3b",
    "gemma3:12b", "gemma3:4b", "llama3.1:8b", "qwen3:8b",
)

# Small instruct model, ~2 GB, good enough to run the guided-question flow
# on a CPU. Override with FRANCESSCA_MODEL_URL / FRANCESSCA_MODEL_FILE if you
# would rather ship something else — any GGUF chat model works.
MODEL_URL = os.environ.get(
    "FRANCESSCA_MODEL_URL",
    "https://huggingface.co/bartowski/Qwen2.5-3B-Instruct-GGUF/resolve/main/"
    "Qwen2.5-3B-Instruct-Q4_K_M.gguf",
)
MODEL_FILE = os.environ.get(
    "FRANCESSCA_MODEL_FILE", "Qwen2.5-3B-Instruct-Q4_K_M.gguf"
)
MODEL_CONTEXT = os.environ.get("FRANCESSCA_MODEL_CTX", "8192")


def _add_backend_to_path() -> None:
    """Run from source as well as frozen.

    PyInstaller bakes backend/ into the executable via the spec's pathex; a
    plain `python desktop/main.py` needs it on sys.path to import `app`.
    """
    if getattr(sys, "frozen", False):
        return
    backend = Path(__file__).resolve().parent.parent / "backend"
    if backend.is_dir() and str(backend) not in sys.path:
        sys.path.insert(0, str(backend))


_add_backend_to_path()


def bundle_dir() -> Path:
    """Where the bundled read-only assets are, frozen or not."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent / "dist-assets"


def data_dir() -> Path:
    """Per-user, writable: database, uploads, model, generated secret."""
    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    elif sys.platform == "darwin":
        root = Path.home() / "Library/Application Support"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    path = root / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def jwt_secret(home: Path) -> str:
    """A per-installation signing key, generated once and kept on disk."""
    key_file = home / "secret.key"
    if not key_file.exists():
        key_file.write_text(secrets.token_urlsafe(48), encoding="utf-8")
        try:  # best effort; Windows ACLs are not POSIX modes
            key_file.chmod(0o600)
        except OSError:
            pass
    return key_file.read_text(encoding="utf-8").strip()


def find_binary(folder: Path, *names: str) -> Path | None:
    for name in names:
        for candidate in (folder / name, folder / "bin" / name):
            if candidate.exists():
                return candidate
    # Fall back to whatever the system has, so a dev run works unpackaged.
    for name in names:
        found = shutil.which(name)
        if found:
            return Path(found)
    return None


def download_model(target: Path) -> None:
    """First run only. Streams to a .part file so an interrupted download
    is never mistaken for a complete model."""
    part = target.with_suffix(target.suffix + ".part")
    print(f"\nDownloading the local model (once, ~2 GB):\n  {MODEL_URL}")
    try:
        with urllib.request.urlopen(MODEL_URL) as response, part.open("wb") as out:
            total = int(response.headers.get("Content-Length") or 0)
            done = 0
            while chunk := response.read(1 << 20):
                out.write(chunk)
                done += len(chunk)
                if total:
                    pct = done * 100 // total
                    print(f"\r  {pct:3d}%  {done >> 20} / {total >> 20} MB", end="")
        print()
    except (urllib.error.URLError, OSError) as exc:
        part.unlink(missing_ok=True)
        sys.exit(
            f"\nCould not download the model: {exc}\n"
            f"Download it manually and save it as:\n  {target}\n"
            f"or set FRANCESSCA_MODEL_URL to a mirror."
        )
    part.replace(target)


def port_open(port: int, timeout: float = 1.0) -> bool:
    with socket.socket() as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((API_HOST, port)) == 0


def detect_ollama() -> str | None:
    """Return the Ollama model to use, if Ollama is running with one.

    Lets someone who already has Ollama skip the bundled server and the 2 GB
    download entirely - the app only needs *an* OpenAI-compatible endpoint.
    """
    if not port_open(OLLAMA_PORT):
        return None
    forced = os.environ.get("FRANCESSCA_OLLAMA_MODEL")
    if forced:
        return forced
    try:
        with urllib.request.urlopen(
            f"http://{API_HOST}:{OLLAMA_PORT}/api/tags", timeout=5
        ) as response:
            names = [m.get("name", "") for m in json.load(response).get("models", [])]
    except (urllib.error.URLError, OSError, ValueError):
        return None
    if not names:
        return None
    for preferred in PREFERRED_OLLAMA_MODELS:
        for name in names:
            if name == preferred or name.startswith(preferred + "-"):
                return name
    return names[0]


def wait_for_port(port: int, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket() as sock:
            sock.settimeout(1.0)
            if sock.connect_ex((API_HOST, port)) == 0:
                return True
        time.sleep(0.5)
    return False


def start_model_server(home: Path) -> subprocess.Popen | None:
    """Launch the bundled llama.cpp server, downloading the model if needed."""
    llama = find_binary(bundle_dir() / "llama", "llama-server", "llama-server.exe")
    if llama is None:
        print(
            "No llama-server binary bundled. Start your own OpenAI-compatible\n"
            f"server on port {LLAMA_PORT} (Ollama, LM Studio, llama.cpp), or\n"
            "rebuild with desktop/build.ps1, which fetches one."
        )
        return None

    model_path = home / MODEL_FILE
    if not model_path.exists():
        download_model(model_path)

    print(f"Starting the local model ({model_path.name})…")
    process = subprocess.Popen(
        [
            str(llama),
            "--model", str(model_path),
            "--host", API_HOST,
            "--port", str(LLAMA_PORT),
            "--ctx-size", MODEL_CONTEXT,
            # Leave one core for the app itself.
            "--threads", str(max(1, (os.cpu_count() or 4) - 1)),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(llama.parent),
    )
    if not wait_for_port(LLAMA_PORT, timeout=180):
        print("The model server did not come up in time; continuing anyway.")
    return process


def configure_environment(home: Path, base_url: str, model_name: str) -> None:
    """Every setting the app reads must be in the environment *before*
    app.config is imported — Settings is built at import time."""
    uploads = home / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)

    env = {
        "DATABASE_URL": f"sqlite:///{(home / 'francessca.db').as_posix()}",
        "JWT_SECRET": jwt_secret(home),
        "UPLOAD_DIR": str(uploads),
        "AI_PROVIDER": "local",
        "LOCAL_AI_BASE_URL": base_url,
        "LOCAL_AI_MODEL": model_name,
        "FRONTEND_DIST": str(bundle_dir() / "frontend"),
        # Same origin, so CORS is irrelevant — but keep it consistent.
        "FRONTEND_URL": f"http://{API_HOST}:{API_PORT}",
        "BACKEND_URL": f"http://{API_HOST}:{API_PORT}",
        "CORS_ORIGINS": f"http://{API_HOST}:{API_PORT}",
        # Offline: no bar-directory scrape, so ship the sample directory.
        "USE_FAKE_LAWYERS_DB": "true",
    }
    fonts = bundle_dir() / "fonts"
    if fonts.is_dir():
        env["FONT_DIR"] = str(fonts)

    tesseract = find_binary(bundle_dir() / "tesseract", "tesseract", "tesseract.exe")
    if tesseract is not None:
        env["TESSERACT_CMD"] = str(tesseract)
        tessdata = tesseract.parent / "tessdata"
        if tessdata.is_dir():
            env.setdefault("TESSDATA_PREFIX", str(tessdata))

    for key, value in env.items():
        os.environ.setdefault(key, value)


def prepare_database() -> None:
    """SQLite gets its schema straight from the models.

    Alembic is for the server deployment: two of its migrations create
    Postgres ENUM types, which SQLite has no notion of.
    """
    from app import models  # noqa: F401  (registers every table)
    from app.bootstrap import run as bootstrap
    from app.database import Base, engine

    Base.metadata.create_all(engine)
    bootstrap()


def main() -> int:
    home = data_dir()
    print(f"{APP_NAME} — offline desktop build")
    print(f"Your data: {home}")

    # Which model server to talk to, in order of preference: whatever the
    # user configured, an Ollama instance they are already running, or the
    # bundled llama.cpp with its own downloaded model.
    model_process = None
    base_url = os.environ.get("LOCAL_AI_BASE_URL")
    model_name = os.environ.get("LOCAL_AI_MODEL", MODEL_FILE)
    if base_url:
        print(f"Using the model server configured in LOCAL_AI_BASE_URL: {base_url}")
    else:
        ollama_model = detect_ollama()
        if ollama_model and find_binary(bundle_dir() / "llama", "llama-server", "llama-server.exe") is None:
            base_url = f"http://{API_HOST}:{OLLAMA_PORT}/v1"
            model_name = ollama_model
            print(f"Using Ollama on port {OLLAMA_PORT} with model '{model_name}'.")
        else:
            base_url = f"http://{API_HOST}:{LLAMA_PORT}/v1"
            model_process = start_model_server(home)

    configure_environment(home, base_url, model_name)

    try:
        prepare_database()

        import uvicorn

        from app.main import app

        url = f"http://{API_HOST}:{API_PORT}/"
        threading.Thread(
            target=lambda: (wait_for_port(API_PORT, 30), webbrowser.open(url)),
            daemon=True,
        ).start()
        print(f"\nFrancessca is running at {url}\nClose this window to stop it.\n")
        uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="warning")
    except KeyboardInterrupt:
        pass
    finally:
        if model_process is not None:
            model_process.terminate()
            try:
                model_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                model_process.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
