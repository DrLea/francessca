<#
    Builds Francesca.exe - the offline desktop build - on Windows.

    Prerequisites:
      * Python 3.11+ on PATH          (python --version)
      * Node.js 20+ on PATH           (node --version)
      * Tesseract-OCR installed, for image OCR:
        https://github.com/UB-Mannheim/tesseract/wiki

    Usage (PowerShell):
      cd $HOME\Desktop\francessca\desktop
      .\build.ps1                     # full build
      .\build.ps1 -SkipFrontend       # reuse the previous UI export
      .\build.ps1 -CleanInstall       # wipe node_modules and reinstall first

    From cmd.exe, run build.cmd instead - same arguments.

    Output: desktop\dist\Francesca.exe

    NOTE: keep this file ASCII-only and saved as UTF-8 with BOM. Windows
    PowerShell 5.1 reads a BOM-less file as ANSI, and a mis-decoded dash or
    quote turns into a curly quote, which PowerShell treats as a string
    delimiter - producing baffling "string is missing the terminator" errors.
#>
[CmdletBinding()]
param(
    [switch]$SkipFrontend,
    # Wipe frontend\node_modules before installing. Use this when the build
    # fails inside node_modules itself (truncated files from an interrupted
    # install): npm repairs a missing package, but never a corrupted one.
    [switch]$CleanInstall,
    # Optional. Left empty, the script resolves the newest CPU build from the
    # llama.cpp releases API itself. Pass a URL to pin a version or to use a
    # GPU build (cuda / vulkan / hip).
    [string]$LlamaZipUrl = $env:LLAMA_ZIP_URL,
    [string]$TesseractDir = "C:\Program Files\Tesseract-OCR"
)

$ErrorActionPreference = "Stop"
$Here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root   = Split-Path -Parent $Here
$Assets = Join-Path $Here "dist-assets"

# Fail early and clearly rather than halfway through a five-minute build.
foreach ($tool in @("node", "npm")) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        throw "$tool is not on PATH. Install Node.js 20+ from nodejs.org, then open a new terminal."
    }
}

# Pick the Python to build with. Newest is not best here: PyInstaller and the
# compiled dependencies (pydantic-core, pillow, lxml) need wheels published
# for that exact version, and a just-released Python often has none. Prefer a
# settled version through the py launcher, fall back to whatever is on PATH.
$PyExe = $null
$PyArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue) {
    foreach ($v in @("3.12", "3.13", "3.11")) {
        try {
            & py "-$v" --version *> $null
            if ($LASTEXITCODE -eq 0) { $PyExe = "py"; $PyArgs = @("-$v"); break }
        } catch { }
    }
}
if (-not $PyExe) {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw "No Python found. Install 3.12 from python.org and tick 'Add python.exe to PATH'."
    }
    $PyExe = "python"
}
$pyVersion = (& $PyExe @PyArgs --version) 2>&1
Write-Host "    building with $pyVersion"
if ($pyVersion -match "3\.(1[4-9]|[2-9][0-9])") {
    Write-Warning @"
That Python is very new. If pip starts compiling packages from source, or
PyInstaller refuses to run, install Python 3.12 from python.org and run this
again - the py launcher will then pick it up automatically.
"@
}
New-Item -ItemType Directory -Force -Path $Assets | Out-Null

Write-Host "==> 1/5  Exporting the frontend" -ForegroundColor Cyan
if (-not $SkipFrontend) {
    Push-Location (Join-Path $Root "frontend")
    if ($CleanInstall -and (Test-Path "node_modules")) {
        Write-Host "    removing node_modules"
        # Deeply nested paths defeat Remove-Item on some setups; rd copes.
        Remove-Item -Recurse -Force "node_modules" -ErrorAction SilentlyContinue
        if (Test-Path "node_modules") { cmd /c rd /s /q node_modules }
    }
    # Run every time: it is quick when the tree is current, and it is what
    # applies a dependency change (a security patch, say) without anyone
    # having to remember to reinstall.
    Write-Host "    installing frontend dependencies (a few minutes the first time)"
    npm install --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { Pop-Location; throw "npm install failed." }
    if (-not (Test-Path "node_modules\.bin\next.cmd")) {
        Pop-Location
        throw "node_modules is incomplete. Delete frontend\node_modules, then run this again."
    }
    # DESKTOP_BUILD makes Next emit a static site; the empty API URL makes the
    # UI call whatever origin serves it, which is the app's own process.
    $env:DESKTOP_BUILD = "1"
    $env:NEXT_PUBLIC_SAME_ORIGIN_API = "1"
    npm run build
    if ($LASTEXITCODE -ne 0) {
        Pop-Location
        throw "The frontend build failed. If the error came from inside node_modules, run: .\build.ps1 -CleanInstall"
    }
    Remove-Item Env:DESKTOP_BUILD, Env:NEXT_PUBLIC_SAME_ORIGIN_API -ErrorAction SilentlyContinue
    Pop-Location

    $frontend = Join-Path $Assets "frontend"
    if (Test-Path $frontend) { Remove-Item -Recurse -Force $frontend }
    Copy-Item -Recurse (Join-Path $Root "frontend\out") $frontend
}

Write-Host "==> 2/5  Collecting the local model server" -ForegroundColor Cyan
$llamaDir = Join-Path $Assets "llama"
New-Item -ItemType Directory -Force -Path $llamaDir | Out-Null
$haveLlama = [bool](Get-ChildItem $llamaDir -Filter "llama-server.exe" -Recurse -ErrorAction SilentlyContinue)

if (-not $haveLlama -and -not $LlamaZipUrl) {
    # Resolve the newest Windows CPU build ourselves so nobody has to go
    # hunting for an asset name that changes with every release.
    try {
        $api = "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest"
        $release = Invoke-RestMethod -Uri $api -Headers @{ "User-Agent" = "francessca-build" }
        $asset = $release.assets | Where-Object { $_.name -match "bin-win-cpu-x64.*\.zip$" } | Select-Object -First 1
        if (-not $asset) {
            $asset = $release.assets | Where-Object { $_.name -match "bin-win.*x64.*\.zip$" } | Select-Object -First 1
        }
        if ($asset) {
            $LlamaZipUrl = $asset.browser_download_url
            Write-Host ("    using " + $asset.name + " from release " + $release.tag_name)
        }
    } catch {
        Write-Warning ("    could not reach the llama.cpp releases API: " + $_.Exception.Message)
    }
}

if ($haveLlama) {
    Write-Host "    already present, skipping download"
} elseif ($LlamaZipUrl) {
    $zip = Join-Path $env:TEMP "llama.zip"
    Invoke-WebRequest -Uri $LlamaZipUrl -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $llamaDir -Force
    Remove-Item $zip
} else {
    Write-Warning @"
No llama-server.exe bundled. Download a CPU release archive from
https://github.com/ggml-org/llama.cpp/releases and either pass it as
-LlamaZipUrl or extract llama-server.exe and its DLLs into
$llamaDir yourself. The build continues without it; the app will then expect
an OpenAI-compatible server (Ollama, LM Studio) on port 8757.
"@
}

Write-Host "==> 3/5  Collecting Tesseract (OCR)" -ForegroundColor Cyan
$tessTarget = Join-Path $Assets "tesseract"
# Take it from PATH if it is there - installers land in various places, and
# "tesseract works in my terminal" should be enough.
if (-not (Test-Path (Join-Path $TesseractDir "tesseract.exe"))) {
    $onPath = Get-Command tesseract -ErrorAction SilentlyContinue
    if ($onPath) {
        $TesseractDir = Split-Path -Parent $onPath.Source
        Write-Host "    found on PATH: $TesseractDir"
    }
}
if (Test-Path (Join-Path $TesseractDir "tesseract.exe")) {
    if (Test-Path $tessTarget) { Remove-Item -Recurse -Force $tessTarget }
    New-Item -ItemType Directory -Force -Path $tessTarget | Out-Null
    Copy-Item (Join-Path $TesseractDir "*") $tessTarget -Recurse
    # Keep only German + English language data; the full set is ~1 GB.
    $tessdata = Join-Path $tessTarget "tessdata"
    if (Test-Path $tessdata) {
        Get-ChildItem $tessdata -Filter "*.traineddata" |
            Where-Object { $_.BaseName -notin @("deu", "eng", "osd") } |
            Remove-Item -Force
        # The app runs OCR as deu+eng; a missing pack fails at runtime, not now.
        foreach ($lang in @("deu", "eng")) {
            if (-not (Test-Path (Join-Path $tessdata "$lang.traineddata"))) {
                Write-Warning "    tessdata\$lang.traineddata is missing - re-run the Tesseract installer and tick that language."
            }
        }
    } else {
        Write-Warning "    no tessdata folder found next to tesseract.exe - OCR will not work."
    }
} else {
    Write-Warning "Tesseract not found at $TesseractDir - image OCR will be unavailable."
}

Write-Host "==> 4/5  Installing Python build dependencies" -ForegroundColor Cyan
$venv = Join-Path $Here ".venv"
if (-not (Test-Path $venv)) {
    & $PyExe @PyArgs -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw "Could not create the build virtualenv." }
}
$py = Join-Path $venv "Scripts\python.exe"
& $py -m pip install --upgrade pip | Out-Null
# requirements-desktop.txt, not the server's pinned list: see the comments
# in that file for why.
& $py -m pip install -r (Join-Path $Here "requirements-desktop.txt")
if ($LASTEXITCODE -ne 0) {
    throw "Installing the Python dependencies failed. If pip was compiling from source, install Python 3.12 from python.org, delete desktop\.venv, and run this again."
}

Write-Host "==> 5/5  Packaging" -ForegroundColor Cyan
# Arguments as an array: no backtick line continuations, which are fragile in
# a CRLF file.
$pyiArgs = @(
    "-m", "PyInstaller", "--noconfirm", "--clean",
    "--distpath", (Join-Path $Here "dist"),
    "--workpath", (Join-Path $Here "build"),
    (Join-Path $Here "francessca.spec")
)
& $py @pyiArgs
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }

Write-Host ""
Write-Host ("Done: " + (Join-Path $Here "dist\Francesca.exe")) -ForegroundColor Green
Write-Host "First launch downloads the model (about 2 GB) into %LOCALAPPDATA%\Francesca."
