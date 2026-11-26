@echo off
REM Double-click to start the Shopify Image Scraper. The first run sets up Python.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Setting up Python environment, one time only...
    python -m venv .venv || (echo Python 3.10+ is required: https://www.python.org/downloads/ & pause & exit /b 1)
    ".venv\Scripts\python" -m pip install -q -r requirements.txt
)
".venv\Scripts\python" shopify_scraper.py %*
echo.
pause
