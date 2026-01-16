# Script chạy Python API với output đầy đủ
Write-Host "Starting Python Vectorize API..." -ForegroundColor Green
Write-Host ""

# Kiểm tra Python
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python không được tìm thấy!" -ForegroundColor Red
    Write-Host "Vui lòng cài đặt Python từ https://www.python.org/" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "Python version: $pythonVersion" -ForegroundColor Cyan
Write-Host ""

# Kiểm tra dependencies
Write-Host "Checking dependencies..." -ForegroundColor Yellow
$flaskInstalled = pip show flask 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing dependencies (this may take a few minutes)..." -ForegroundColor Yellow
    pip install flask flask-cors sentence-transformers numpy torch
    Write-Host ""
}

# Chạy server
Write-Host "Starting server on http://localhost:5005..." -ForegroundColor Green
Write-Host "NOTE: First run will download model (~400MB), please wait..." -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop" -ForegroundColor Cyan
Write-Host ""

python app.py
