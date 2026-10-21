@echo off
REM Double-click to start Jarvis on Windows. Sets everything up the first time.
cd /d "%~dp0"
if not exist .venv (
    echo Setting up Jarvis for the first time...
    py -3 -m venv .venv || python -m venv .venv
    .venv\Scripts\python -m pip install --upgrade pip
    .venv\Scripts\python -m pip install -r requirements.txt
)
if not exist .env (
    copy .env.example .env >nul
    echo.
    echo Opening .env - paste your Anthropic API key there, save, then run this again.
    notepad .env
    exit /b
)
.venv\Scripts\python -m jarvis
pause
