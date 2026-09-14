@echo off
REM ============================================================
REM  Agent Forge - local runner (Windows)
REM
REM  Reads provider settings from .env (never commit that file).
REM  Copy .env.example to .env and fill in your own values.
REM
REM  Usage:
REM    forge.cmd build "My task description" --refine
REM    forge.cmd list
REM    forge.cmd show <slug>
REM ============================================================

setlocal

REM Load .env if present (KEY=VALUE per line, '#' comments ignored)
if exist "%~dp0.env" (
  for /f "usebackq tokens=1,* delims==" %%A in ("%~dp0.env") do (
    echo %%A | findstr /b /c:"#" >nul || set "%%A=%%B"
  )
)

REM Defaults for a local Ollama setup (override via .env)
if not defined FORGE_BASE_URL set "FORGE_BASE_URL=http://localhost:11434/v1"
if not defined FORGE_MODEL set "FORGE_MODEL=qwen2.5:3b"
if not defined FORGE_MAX_TOKENS set "FORGE_MAX_TOKENS=4096"
if not defined FORGE_TEMPERATURE set "FORGE_TEMPERATURE=0.2"
if not defined FORGE_TIMEOUT set "FORGE_TIMEOUT=600"
if not defined FORGE_API_KEY set "FORGE_API_KEY="

cd /d "%~dp0"
python -m forge %*

endlocal
