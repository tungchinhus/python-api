@echo off
echo ========================================
echo Starting Python API Server
echo ========================================
echo.

REM Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run: python -m venv venv
    echo Then: venv\Scripts\activate
    echo Then: pip install -r requirements.txt
    pause
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Checking dependencies...
python -c "from sentence_transformers import SentenceTransformer; print('OK: Dependencies ready')" 2>nul
if errorlevel 1 (
    echo WARNING: Dependencies may need update
    echo Running: pip install --upgrade sentence-transformers huggingface_hub
    pip install --upgrade sentence-transformers huggingface_hub --quiet
)

echo.
echo ========================================
echo Starting Python API on port 5005...
echo ========================================
echo.
python app.py

pause
