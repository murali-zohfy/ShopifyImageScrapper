@echo off
REM Double-click to start the scraper. First run creates the Python environment.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Setting up Python environment, one time only...
    python -m venv .venv || (echo Python 3.10+ is required: https://www.python.org/downloads/ & pause & exit /b 1)
    ".venv\Scripts\pip" install -q -r requirements.txt
)
".venv\Scripts\python" scraper.py %*
echo.
pause
