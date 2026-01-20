# Hướng Dẫn Tích Hợp RAG System với Firebase Functions

## 📋 Tổng Quan

RAG System đã được cập nhật để hỗ trợ **GEMINI_API_KEY** từ Firebase Functions Secret Manager, giúp tích hợp tốt hơn với hệ thống hiện tại.

## ✅ Đã Cập Nhật

RAG System hiện hỗ trợ cả 2 cách lấy API key:
1. `GOOGLE_API_KEY` - Từ .env file (local development)
2. `GEMINI_API_KEY` - Từ Firebase Functions Secret Manager (production)

## 🔧 Cấu Hình

### Option 1: Dùng GEMINI_API_KEY từ Firebase (Khuyến nghị)

Nếu đã có `GEMINI_API_KEY` trong Firebase Functions, chỉ cần set environment variable:

**Windows:**
```powershell
$env:GEMINI_API_KEY = "your_api_key_here"
```

**Linux/Mac:**
```bash
export GEMINI_API_KEY="your_api_key_here"
```

**Hoặc trong .env file:**
```env
GEMINI_API_KEY=your_api_key_here
```

### Option 2: Dùng GOOGLE_API_KEY (Local Development)

```env
GOOGLE_API_KEY=your_api_key_here
```

## 🚀 Sử Dụng với Firebase Functions

### 1. Lấy GEMINI_API_KEY từ Firebase Secret Manager

Nếu đã có secret trong Firebase:

```bash
# Xem secret (cần quyền)
firebase functions:secrets:access GEMINI_API_KEY
```

### 2. Set Environment Variable cho Python Service

**Option A: Export trực tiếp**
```bash
# Lấy từ Firebase và set
export GEMINI_API_KEY=$(firebase functions:secrets:access GEMINI_API_KEY)
python rag_main_sql.py
```

**Option B: Tạo .env từ Firebase secret**
```bash
# Tạo script get-secret.sh
#!/bin/bash
echo "GEMINI_API_KEY=$(firebase functions:secrets:access GEMINI_API_KEY)" > .env
```

**Option C: Dùng trong Docker/Container**
```dockerfile
# Dockerfile
RUN firebase functions:secrets:access GEMINI_API_KEY > /tmp/gemini_key
ENV GEMINI_API_KEY=$(cat /tmp/gemini_key)
```

### 3. Chạy RAG Service

```bash
# RAG với SQL Server Vector
python rag_main_sql.py

# Hoặc RAG với ChromaDB
python rag_main.py
```

## 🔄 Tích Hợp với Firebase Functions

### Option 1: Tạo Firebase Function mới cho RAG

Tạo function mới trong `functions/index.js`:

```javascript
const {onRequest} = require("firebase-functions/v2/https");
const {defineSecret} = require("firebase-functions/params");

// Define secret
const geminiApiKey = defineSecret("GEMINI_API_KEY");

exports.ragIngest = onRequest(
  {
    cors: true,
    secrets: [geminiApiKey],
  },
  async (req, res) => {
    // Gọi Python service hoặc implement logic trực tiếp
    const apiKey = geminiApiKey.value();
    
    // Call Python RAG service
    const response = await fetch("http://localhost:8000/ingest", {
      method: "POST",
      headers: {
        "X-API-Key": apiKey, // Pass API key nếu cần
      },
    });
    
    const result = await response.json();
    res.json(result);
  }
);

exports.ragChat = onRequest(
  {
    cors: true,
    secrets: [geminiApiKey],
  },
  async (req, res) => {
    const {query} = req.body;
    
    // Call Python RAG service
    const response = await fetch("http://localhost:8000/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({query}),
    });
    
    const result = await response.json();
    res.json(result);
  }
);
```

### Option 2: Dùng chung GEMINI_API_KEY

Nếu Python service chạy trên cùng server với Firebase Functions, có thể dùng chung environment variable:

```javascript
// functions/index.js
exports.ragService = onRequest(
  {
    cors: true,
    secrets: ["GEMINI_API_KEY"],
  },
  async (req, res) => {
    // GEMINI_API_KEY đã có sẵn trong process.env
    // Python service sẽ tự động lấy từ environment
    // ...
  }
);
```

## 🔐 Security Best Practices

### 1. Không hardcode API key trong code

❌ **Sai:**
```python
api_key = "AIzaSy..."  # Không bao giờ làm thế này!
```

✅ **Đúng:**
```python
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
```

### 2. Sử dụng Secret Manager

✅ **Firebase Functions:**
```javascript
const geminiApiKey = defineSecret("GEMINI_API_KEY");
```

✅ **Python (.env file, không commit vào git):**
```env
GEMINI_API_KEY=your_key_here
```

### 3. Kiểm tra .gitignore

Đảm bảo `.env` đã có trong `.gitignore`:

```gitignore
.env
.env.local
*.key
```

## 📝 Environment Variables Priority

RAG System sẽ tìm API key theo thứ tự:

1. **Parameter truyền vào** (nếu có)
2. **GEMINI_API_KEY** (Firebase Functions)
3. **GOOGLE_API_KEY** (Local development)

```python
# Trong rag_service_sql.py và rag_service.py
api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
```

## 🧪 Testing

### Test với GEMINI_API_KEY

```bash
# Set environment variable
export GEMINI_API_KEY="your_key"

# Test
python -c "import os; print('API Key:', os.getenv('GEMINI_API_KEY'))"
```

### Test RAG Service

```bash
# Start service
python rag_main_sql.py

# Test health check
curl http://localhost:8000/health

# Test ingest
curl -X POST http://localhost:8000/ingest

# Test chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Test query"}'
```

## 🔄 Migration từ GOOGLE_API_KEY sang GEMINI_API_KEY

Nếu đang dùng `GOOGLE_API_KEY` và muốn chuyển sang `GEMINI_API_KEY`:

1. **Lấy key từ Firebase:**
   ```bash
   firebase functions:secrets:access GEMINI_API_KEY
   ```

2. **Update .env:**
   ```env
   # Thay đổi từ
   GOOGLE_API_KEY=old_key
   
   # Sang
   GEMINI_API_KEY=new_key
   ```

3. **Restart service:**
   ```bash
   python rag_main_sql.py
   ```

## 📚 Tài Liệu Tham Khảo

- [Firebase Functions Secrets](https://firebase.google.com/docs/functions/config-env#secret-manager)
- [Google Gemini API](https://ai.google.dev/docs)
- [RAG System Documentation](README_RAG_SQL.md)

## ✅ Checklist

- [x] Hỗ trợ GEMINI_API_KEY từ Firebase
- [x] Hỗ trợ GOOGLE_API_KEY (backward compatible)
- [x] Auto-detect API key từ environment
- [x] Security best practices
- [x] Documentation

## 🎯 Kết Luận

RAG System giờ đã tích hợp tốt với Firebase Functions, có thể dùng chung `GEMINI_API_KEY` mà không cần cấu hình thêm. Chỉ cần set environment variable `GEMINI_API_KEY` và service sẽ tự động sử dụng.
