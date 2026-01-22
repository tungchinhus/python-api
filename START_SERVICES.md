# Hướng Dẫn: Khởi Động Các Services

## 🚀 Vấn đề

Khi test, bạn gặp lỗi:
- `Connection refused` tại `http://localhost:8000` (RAG API)
- `500 Internal Server Error` tại `http://localhost:5005` (Python API)

## ✅ Giải pháp: Khởi động các services

### 1. Khởi động Python API (Port 5005)

**Cách 1: Dùng batch file**
```bash
START_PYTHON_API.bat
```

**Cách 2: Chạy trực tiếp**
```bash
python app.py
```

**Cách 3: Dùng PowerShell**
```powershell
.\run.ps1
```

**Kiểm tra:**
```bash
curl http://localhost:5005/health
# Hoặc mở browser: http://localhost:5005/health
```

### 2. Khởi động RAG API (Port 8000)

**Cách 1: Dùng batch file**
```bash
start_rag.bat
```

**Cách 2: Chạy trực tiếp**
```bash
python rag_main_sql.py
```

**Cách 3: Dùng uvicorn**
```bash
uvicorn rag_main_sql:app --host 0.0.0.0 --port 8000 --reload
```

**Kiểm tra:**
```bash
curl http://localhost:8000/health
# Hoặc mở browser: http://localhost:8000/health
```

## 📋 Checklist trước khi chạy

### 1. Kiểm tra dependencies

```bash
pip install -r requirements.txt
```

**Các package quan trọng:**
- `fastapi`, `uvicorn` (cho RAG API)
- `flask`, `flask-cors` (cho Python API)
- `sentence-transformers` (cho embeddings)
- `pyodbc` (cho SQL Server)
- `langchain`, `langchain-google-genai` (cho RAG)

### 2. Kiểm tra file `.env`

Đảm bảo có các biến môi trường:

```env
# SQL Server
SQL_SERVER=localhost
SQL_DATABASE=THITHI_AI
SQL_TRUSTED_CONNECTION=yes
# Hoặc
# SQL_CONNECTION_STRING=DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=THITHI_AI;Trusted_Connection=yes;TrustServerCertificate=yes;

# Google Gemini API (cho LLM)
GOOGLE_API_KEY=your_api_key_here
# Hoặc
# GEMINI_API_KEY=your_api_key_here

# Python API URL
PYTHON_API_URL=http://localhost:5005/vectorize

# RAG Table
RAG_TABLE_NAME=rag_documents

# Ports
PORT=5005  # Python API
# RAG API port được set trong rag_main_sql.py (mặc định 8000)
```

### 3. Kiểm tra SQL Server

```sql
-- Kiểm tra database tồn tại
SELECT name FROM sys.databases WHERE name = 'THITHI_AI';

-- Kiểm tra bảng
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dbo';
```

## 🔧 Troubleshooting

### Lỗi: "Port already in use"

**Giải pháp:**
```bash
# Windows: Tìm process đang dùng port
netstat -ano | findstr :8000
netstat -ano | findstr :5005

# Kill process
taskkill /PID <PID> /F
```

### Lỗi: "Module not found"

**Giải pháp:**
```bash
# Cài đặt lại dependencies
pip install -r requirements.txt

# Hoặc cài từng package
pip install fastapi uvicorn flask flask-cors sentence-transformers pyodbc langchain langchain-google-genai python-dotenv
```

### Lỗi: "Cannot connect to SQL Server"

**Giải pháp:**
1. Kiểm tra SQL Server đang chạy
2. Kiểm tra connection string trong `.env`
3. Kiểm tra firewall
4. Test connection:
   ```python
   import pyodbc
   conn = pyodbc.connect("DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=THITHI_AI;Trusted_Connection=yes;TrustServerCertificate=yes;")
   print("Connected!")
   ```

### Lỗi: "Google API key not found"

**Giải pháp:**
1. Lấy API key từ Google AI Studio: https://makersuite.google.com/app/apikey
2. Thêm vào `.env`:
   ```env
   GOOGLE_API_KEY=your_api_key_here
   ```

### Lỗi: "Model not loaded" (Python API)

**Giải pháp:**
- Model sẽ tự động download lần đầu
- Đảm bảo có internet
- Kiểm tra disk space (model ~400MB)

## 🎯 Script khởi động tự động

Tạo file `start_all.bat`:

```batch
@echo off
echo Starting all services...

echo Starting Python API (port 5005)...
start "Python API" cmd /k "python app.py"

timeout /t 5

echo Starting RAG API (port 8000)...
start "RAG API" cmd /k "python rag_main_sql.py"

echo.
echo Services started!
echo Python API: http://localhost:5005
echo RAG API: http://localhost:8000
echo.
pause
```

## 📊 Kiểm tra services đang chạy

**Script kiểm tra:**
```python
import requests

services = [
    ("Python API", "http://localhost:5005/health"),
    ("RAG API", "http://localhost:8000/health")
]

for name, url in services:
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"✅ {name}: OK")
        else:
            print(f"⚠️ {name}: Status {response.status_code}")
    except Exception as e:
        print(f"❌ {name}: {e}")
```

## 🎯 Tóm tắt

**Để chạy Chat AI:**

1. ✅ Khởi động Python API: `python app.py` (port 5005)
2. ✅ Khởi động RAG API: `python rag_main_sql.py` (port 8000)
3. ✅ Kiểm tra health: `curl http://localhost:8000/health`
4. ✅ Test chat: `python test_chat_table.py`

**Thứ tự khởi động:**
```
Python API (5005) → RAG API (8000)
```

Python API cần chạy trước vì RAG API cần nó để tạo embeddings.
