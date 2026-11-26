#!/usr/bin/env sh
# macOS / Linux: ./run.sh  (the first run sets up Python)
cd "$(dirname "$0")" || exit 1
if [ ! -x .venv/bin/python ]; then
  echo "Setting up Python environment, one time only..."
  python3 -m venv .venv || { echo "Python 3.10+ is required: https://www.python.org/downloads/"; exit 1; }
  .venv/bin/python -m pip install -q -r requirements.txt
fi
exec .venv/bin/python shopify_scraper.py "$@"
