@echo off
SETLOCAL

echo ----------------------------------------
echo   UNDEAD ARCHIVE — STARTING...
echo ----------------------------------------

IF NOT EXIST .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

echo Activating virtual environment...
call .venv\Scripts\activate

echo Checking dependencies...
pip install --quiet --disable-pip-version-check -r requirements.txt

echo Starting Streamlit app...
streamlit run app.py

echo.
echo 🦇 Undead Archive terminated. Farewell, wanderer.
timeout /t 2 >nul

pause
