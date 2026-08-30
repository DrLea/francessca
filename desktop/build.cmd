@echo off
REM Runs build.ps1 from cmd.exe or a double-click, without changing the
REM machine's PowerShell execution policy. Arguments pass through:
REM     build.cmd -SkipFrontend
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1" %*
if errorlevel 1 (
  echo.
  echo Build failed. Scroll up for the first red line - that is the cause.
)
pause
