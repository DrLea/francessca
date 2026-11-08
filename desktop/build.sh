#!/usr/bin/env bash
# Build the offline desktop binary for the machine you run this on.
# Linux/macOS; the Windows equivalent is build.ps1. PyInstaller does not
# cross-compile — a Windows .exe has to be built on Windows.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
ASSETS="$HERE/dist-assets"

LLAMA_ZIP_URL="${LLAMA_ZIP_URL:-}"   # optional: a llama.cpp release archive
SKIP_FRONTEND="${SKIP_FRONTEND:-0}"

echo "==> 1/4  Exporting the frontend"
if [ "$SKIP_FRONTEND" != "1" ]; then
  pushd "$ROOT/frontend" >/dev/null
  [ -d node_modules ] || npm install --no-audit --no-fund
  # SAME_ORIGIN => the UI calls whatever origin serves it, i.e. the app itself.
  DESKTOP_BUILD=1 NEXT_PUBLIC_SAME_ORIGIN_API=1 npm run build
  popd >/dev/null
  rm -rf "$ASSETS/frontend"
  mkdir -p "$ASSETS"
  cp -r "$ROOT/frontend/out" "$ASSETS/frontend"
fi

echo "==> 2/4  Collecting the local model server"
mkdir -p "$ASSETS/llama"
if [ -n "$LLAMA_ZIP_URL" ]; then
  tmp="$(mktemp -d)"
  curl -fL "$LLAMA_ZIP_URL" -o "$tmp/llama.zip"
  unzip -qo "$tmp/llama.zip" -d "$ASSETS/llama"
  rm -rf "$tmp"
elif command -v llama-server >/dev/null 2>&1; then
  cp "$(command -v llama-server)" "$ASSETS/llama/"
else
  echo "    no llama-server found — set LLAMA_ZIP_URL or install one."
  echo "    (the build continues; the app will ask for an OpenAI-compatible"
  echo "     server on port 8757 instead)"
fi

echo "==> 3/4  Collecting tesseract (OCR)"
mkdir -p "$ASSETS/tesseract"
if command -v tesseract >/dev/null 2>&1; then
  cp "$(command -v tesseract)" "$ASSETS/tesseract/" 2>/dev/null || true
  for dir in /usr/share/tesseract-ocr/*/tessdata /usr/share/tessdata; do
    [ -d "$dir" ] && cp -r "$dir" "$ASSETS/tesseract/tessdata" && break
  done
else
  echo "    tesseract not installed — image OCR will be unavailable."
fi

echo "==> 4/4  Packaging"
python3 -m PyInstaller --noconfirm --clean \
  --distpath "$HERE/dist" --workpath "$HERE/build" \
  "$HERE/francessca.spec"

echo
echo "Done: $HERE/dist/Francesca"
