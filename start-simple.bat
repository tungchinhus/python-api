@echo off
echo ========================================
echo   Starting Python Vectorize API
echo   Port: 5005
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found! Please install Python 3.x
    pause
    exit /b 1
)

echo [2/3] Activating virtual environment...
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run: python -m venv venv
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo [3/3] Starting Python API Server...
echo.
echo NOTE: First time may take a few minutes to download the model.
echo       The server will be available at: http://localhost:5005
echo.
echo Press Ctrl+C to stop the server.
echo.

python app.py

pause
