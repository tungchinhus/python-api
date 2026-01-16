@echo off
echo Starting Python Vectorize API...
echo.

REM Kiểm tra virtual environment
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    echo Virtual environment created.
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Kiểm tra dependencies
echo Checking dependencies...
pip show flask >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
    echo.
)

REM Chạy server
echo Starting server on http://localhost:5005...
echo Press Ctrl+C to stop
echo.
python app.py

pause
