#!/bin/bash

echo "----------------------------------------"
echo "  UNDEAD ARCHIVE — STARTING..."
echo "----------------------------------------"

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

echo "Activating virtual environment..."
# shellcheck disable=SC1091
source .venv/bin/activate

echo "Checking dependencies..."
pip install --quiet --disable-pip-version-check -r requirements.txt

echo "Starting Streamlit app..."
streamlit run app.py
echo "🦇 Undead Archive terminated. Farewell, wanderer."
sleep 2
