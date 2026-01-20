@echo off
echo Starting RAG System...
echo.

REM Kiểm tra .env file
if not exist .env (
    echo ERROR: .env file not found!
    echo Please copy .env.example to .env and add your GOOGLE_API_KEY
    pause
    exit /b 1
)

REM Kiểm tra thư mục data
if not exist data (
    echo Creating data directory...
    mkdir data
    echo Please add PDF files to the data/ directory
)

REM Khởi động server
echo Starting FastAPI server on http://localhost:8000
echo API Documentation: http://localhost:8000/docs
echo.
python rag_main.py

pause
