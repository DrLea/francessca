# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the offline desktop build.

Run it through desktop/build.ps1 (Windows) or desktop/build.sh (Linux/macOS)
rather than directly: those scripts populate dist-assets/ first.
"""
from pathlib import Path

SPEC_DIR = Path(SPECPATH).resolve()
ASSETS = SPEC_DIR / "dist-assets"

# Only what exists gets bundled, so a build without OCR or without the model
# server still produces a working executable.
datas = []
for name in ("frontend", "llama", "tesseract"):
    folder = ASSETS / name
    if folder.is_dir():
        datas.append((str(folder), name))

hiddenimports = [
    # uvicorn resolves these by name at runtime, so PyInstaller cannot see them.
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
    # SQLAlchemy picks the dialect from the URL string.
    "sqlalchemy.dialects.sqlite",
    # Imported lazily inside the extraction helpers.
    "pytesseract",
    "pypdf",
    "docx",
    "PIL.Image",
    "reportlab.pdfbase._fontdata",
    # Arabic PDF export and the routes that import their services lazily.
    "arabic_reshaper",
    "bidi.algorithm",
    "app.services.reply_service",
    "app.services.reminder_service",
]
try:  # arabic_reshaper ships its letter tables / config as data files
    from PyInstaller.utils.hooks import collect_data_files

    datas += collect_data_files("arabic_reshaper")
except Exception:  # noqa: BLE001
    pass

a = Analysis(
    ["main.py"],
    pathex=[str(SPEC_DIR.parent / "backend")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    # Nothing in the desktop build talks to Postgres or Redis.
    excludes=["psycopg", "psycopg2", "tkinter", "matplotlib", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Francesca",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # A console window: the first run downloads the model and prints progress,
    # and it is where the user sees that the app is still running.
    console=True,
    icon=str(SPEC_DIR / "icon.ico") if (SPEC_DIR / "icon.ico").exists() else None,
)
