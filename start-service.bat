@echo off
echo ========================================
echo Starting Python Vectorize API Service
echo ========================================
echo.

cd /d "%~dp0"

REM Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Creating virtual environment...
    python -m venv venv
    echo.
    echo Installing dependencies...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    echo.
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Checking dependencies...
python -c "import flask; import werkzeug; from sentence_transformers import SentenceTransformer; print('OK: Dependencies ready')" 2>nul
if errorlevel 1 (
    echo WARNING: Dependencies may need update
    echo Installing/updating dependencies...
    pip install -r requirements.txt
)

echo.
echo ========================================
echo Starting Python API on port 5005...
echo ========================================
echo.
echo Service will be available at: http://localhost:5005
echo Press Ctrl+C to stop
echo.

python app.py

pause
