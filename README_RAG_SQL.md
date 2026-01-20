# RAG System với SQL Server 2025 Vector

Hệ thống RAG sử dụng **SQL Server 2025 Vector** thay vì ChromaDB để tích hợp tốt hơn với hệ thống hiện tại.

## 🎯 Ưu điểm của SQL Server Vector

- ✅ **Tích hợp tốt**: Dùng chung database với hệ thống .NET backend
- ✅ **Native Vector Search**: Sử dụng `VECTOR_DISTANCE` function của SQL Server 2025
- ✅ **AI_GENERATE_EMBEDDINGS**: Có thể dùng ONNX model trực tiếp trong SQL Server
- ✅ **Không cần ChromaDB**: Giảm dependencies và complexity
- ✅ **Unified Storage**: Tất cả data ở một nơi

## 📋 Yêu cầu
cd cd
- Python 3.8+
- SQL Server 2025 (version >= 16.0) với VECTOR support
- Google Gemini API Key (cho LLM generation)
- ODBC Driver 17 for SQL Server (hoặc mới hơn)

## 🔧 Cài đặt

### 1. Cài đặt dependencies

```bash
pip install -r requirements_rag.txt
```

### 2. Cài đặt ODBC Driver

**Windows:**
- Download từ: https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
- Hoặc dùng: `choco install sqlserver-odbc`

**Linux:**
```bash
# Ubuntu/Debian
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql17
```

### 3. Cấu hình SQL Server

Đảm bảo SQL Server 2025 đã được setup với:
- ONNX Provider enabled
- EXTERNAL MODEL cho embeddings (xem `CREATE_ONNX_MODEL.sql`)

### 4. Cấu hình .env

Tạo file `.env` từ template:

```bash
copy env_template.txt .env
```

Chỉnh sửa `.env`:

```env
# Google Gemini API Key (cho LLM)
GOOGLE_API_KEY=your_google_api_key_here

# SQL Server Connection
SQL_SERVER=localhost
SQL_DATABASE=THITHI_AI
SQL_TRUSTED_CONNECTION=yes

# Hoặc dùng connection string đầy đủ
# SQL_CONNECTION_STRING=DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=THITHI_AI;Trusted_Connection=yes;TrustServerCertificate=yes;

# RAG Configuration
RAG_TABLE_NAME=rag_documents
DATA_DIR=./data

# Embedding: Dùng SQL Server AI_GENERATE_EMBEDDINGS hay Python API?
USE_SQL_EMBEDDINGS=true  # true = dùng SQL Server, false = dùng Python API
EMBEDDING_MODEL_NAME=local_onnx_embeddings
EMBEDDING_DIMENSION=384

# Nếu USE_SQL_EMBEDDINGS=false, cần Python API URL
PYTHON_API_URL=http://localhost:5005/vectorize
```

## 🚀 Sử dụng

### 1. Khởi động server

```bash
python rag_main_sql.py
```

Hoặc với uvicorn:

```bash
uvicorn rag_main_sql:app --reload --port 8000
```

### 2. Ingest PDF files

**Endpoint:** `POST /ingest`

```bash
curl -X POST "http://localhost:8000/ingest"
```

Hệ thống sẽ:
- Quét tất cả PDF trong `./data`
- Chia nhỏ thành chunks
- Generate embeddings (SQL Server hoặc Python API)
- Lưu vào SQL Server với VECTOR type

**Response:**
```json
{
  "status": "success",
  "message": "Đã ingest thành công 45 chunks từ 3 files",
  "total_documents": 3,
  "total_chunks": 45,
  "total_files": 3,
  "files": ["document1.pdf", "document2.pdf", "document3.pdf"]
}
```

### 3. Chat với RAG system

**Endpoint:** `POST /chat`

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Máy bơm có công suất bao nhiêu?"
  }'
```

Hệ thống sẽ:
- Generate embedding cho query
- Tìm kiếm bằng `VECTOR_DISTANCE` trong SQL Server
- Generate answer với Gemini
- Trả về answer + sources

**Response:**
```json
{
  "answer": "Theo tài liệu, máy bơm có công suất 5HP...",
  "sources": [
    {
      "file_name": "manual.pdf",
      "page_number": 5,
      "content_preview": "Máy bơm Model X có công suất 5HP..."
    }
  ],
  "query": "Máy bơm có công suất bao nhiêu?"
}
```

## 🗄️ Database Schema

Bảng `rag_documents` sẽ có cấu trúc:

```sql
CREATE TABLE dbo.[rag_documents] (
    ID INT IDENTITY(1,1) PRIMARY KEY,
    Content NVARCHAR(MAX) NOT NULL,
    VectorJson NVARCHAR(MAX) NULL,        -- Backup embedding (JSON)
    Embedding VECTOR(384) NULL,            -- Native VECTOR type (SQL Server 2025)
    FileName NVARCHAR(500) NULL,
    PageNumber INT NULL,
    ChunkIndex INT NULL,
    CreatedAt DATETIME2 DEFAULT GETDATE()
);
```

## 🔍 Vector Search

Hệ thống sử dụng `VECTOR_DISTANCE` function của SQL Server 2025:

```sql
SELECT TOP (4)
    ID, Content, FileName, PageNumber,
    (1.0 - VECTOR_DISTANCE(Embedding, CAST(@queryVector AS VECTOR(384)), COSINE)) AS Similarity
FROM dbo.[rag_documents]
WHERE Embedding IS NOT NULL
ORDER BY VECTOR_DISTANCE(Embedding, CAST(@queryVector AS VECTOR(384)), COSINE) ASC
```

## ⚙️ Cấu hình Embedding

### Option 1: Dùng SQL Server AI_GENERATE_EMBEDDINGS

**Ưu điểm:**
- Không cần Python API
- Embedding được generate trực tiếp trong SQL Server
- Sử dụng ONNX model đã setup

**Cấu hình:**
```env
USE_SQL_EMBEDDINGS=true
EMBEDDING_MODEL_NAME=local_onnx_embeddings
EMBEDDING_DIMENSION=384
```

**Yêu cầu:**
- SQL Server 2025 với ONNX Provider enabled
- EXTERNAL MODEL đã được tạo (xem `CREATE_ONNX_MODEL.sql`)

### Option 2: Dùng Python API

**Ưu điểm:**
- Linh hoạt hơn, có thể dùng nhiều embedding models
- Không phụ thuộc vào SQL Server ONNX setup

**Cấu hình:**
```env
USE_SQL_EMBEDDINGS=false
PYTHON_API_URL=http://localhost:5005/vectorize
```

**Yêu cầu:**
- Python API service đang chạy (app.py với /vectorize endpoint)

## 📊 So sánh với ChromaDB version

| Tính năng | ChromaDB | SQL Server Vector |
|-----------|----------|-------------------|
| Storage | Local file (./db) | SQL Server database |
| Integration | Standalone | Tích hợp với .NET backend |
| Vector Search | ChromaDB native | SQL Server VECTOR_DISTANCE |
| Embedding | Python API hoặc Gemini | SQL Server AI_GENERATE_EMBEDDINGS hoặc Python API |
| Scalability | Limited | Enterprise-grade |
| Backup | Manual | SQL Server backup |

## 🐛 Troubleshooting

### Lỗi: "ODBC Driver not found"

**Giải pháp:**
- Cài đặt ODBC Driver 17 for SQL Server
- Kiểm tra connection string có đúng driver name không

### Lỗi: "Cannot find EXTERNAL MODEL"

**Giải pháp:**
- Chạy script `CREATE_ONNX_MODEL.sql` để tạo EXTERNAL MODEL
- Hoặc set `USE_SQL_EMBEDDINGS=false` để dùng Python API

### Lỗi: "VECTOR type not supported"

**Giải pháp:**
- Đảm bảo SQL Server version >= 16.0 (SQL Server 2025)
- Kiểm tra: `SELECT @@VERSION`

### Lỗi: "Python API not available"

**Giải pháp:**
- Nếu `USE_SQL_EMBEDDINGS=false`, đảm bảo Python API đang chạy
- Hoặc set `USE_SQL_EMBEDDINGS=true` để dùng SQL Server embeddings

## 🔄 Migration từ ChromaDB

Nếu đã có data trong ChromaDB và muốn chuyển sang SQL Server:

1. Export data từ ChromaDB (nếu cần)
2. Chạy `/ingest` lại để import vào SQL Server
3. Data sẽ được lưu vào bảng `rag_documents`

## 📝 API Reference

Xem `README_RAG.md` để biết chi tiết về API endpoints (tương tự, chỉ khác storage backend).

## 🚀 Next Steps

- [ ] Thêm vector index để tăng tốc độ search
- [ ] Support multiple tables/collections
- [ ] Thêm metadata filtering
- [ ] Thêm batch import
- [ ] Thêm update/delete documents

## 📄 License

MIT
