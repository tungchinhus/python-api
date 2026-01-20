# PowerShell script để khởi động RAG System

Write-Host "Starting RAG System..." -ForegroundColor Green
Write-Host ""

# Kiểm tra .env file
if (-not (Test-Path ".env")) {
    Write-Host "ERROR: .env file not found!" -ForegroundColor Red
    Write-Host "Please copy .env.example to .env and add your GOOGLE_API_KEY" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Kiểm tra thư mục data
if (-not (Test-Path "data")) {
    Write-Host "Creating data directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path "data" | Out-Null
    Write-Host "Please add PDF files to the data/ directory" -ForegroundColor Yellow
    Write-Host ""
}

# Khởi động server
Write-Host "Starting FastAPI server on http://localhost:8000" -ForegroundColor Cyan
Write-Host "API Documentation: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""

python rag_main.py

Read-Host "Press Enter to exit"
