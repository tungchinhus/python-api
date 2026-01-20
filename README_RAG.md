# RAG System - Retrieval-Augmented Generation với Gemini và ChromaDB

Hệ thống RAG hoàn chỉnh để tìm kiếm và trả lời câu hỏi dựa trên tài liệu PDF.

## 🚀 Tính năng

- ✅ Quét và xử lý tự động tất cả file PDF trong thư mục `./data`
- ✅ Chia nhỏ text thành chunks với overlap để giữ context
- ✅ Tạo embeddings bằng Google Gemini `text-embedding-004`
- ✅ Lưu trữ vector trong ChromaDB (local)
- ✅ Tìm kiếm semantic và generate answer với Gemini `1.5-flash`
- ✅ Trả về sources (tên file, số trang) để đối chiếu

## 📋 Yêu cầu

- Python 3.8+
- Google Gemini API Key (lấy tại: https://makersuite.google.com/app/apikey)

## 🔧 Cài đặt

### 1. Cài đặt dependencies

```bash
pip install -r requirements_rag.txt
```

### 2. Cấu hình API Key

Tạo file `.env` từ template:

```bash
cp .env.example .env
```

Chỉnh sửa `.env` và thêm Google API Key:

```env
GOOGLE_API_KEY=your_google_api_key_here
```

### 3. Chuẩn bị thư mục data

Tạo thư mục `data` và đặt các file PDF vào đó:

```bash
mkdir data
# Copy các file PDF vào thư mục data/
```

## 🎯 Sử dụng

### 1. Khởi động server

```bash
python rag_main.py
```

Hoặc với uvicorn trực tiếp:

```bash
uvicorn rag_main:app --reload --port 8000
```

Server sẽ chạy tại: `http://localhost:8000`

### 2. API Documentation

Truy cập Swagger UI tại: `http://localhost:8000/docs`

Hoặc ReDoc tại: `http://localhost:8000/redoc`

### 3. Ingest PDF files

**Endpoint:** `POST /ingest`

Quét tất cả PDF trong `./data` và lưu vào ChromaDB:

```bash
curl -X POST "http://localhost:8000/ingest"
```

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

### 4. Chat với RAG system

**Endpoint:** `POST /chat`

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Máy bơm có công suất bao nhiêu?"
  }'
```

**Response:**
```json
{
  "answer": "Theo tài liệu, máy bơm có công suất 5HP...",
  "sources": [
    {
      "file_name": "manual.pdf",
      "page_number": 5,
      "content_preview": "Máy bơm Model X có công suất 5HP..."
    },
    {
      "file_name": "specs.pdf",
      "page_number": 2,
      "content_preview": "Thông số kỹ thuật: Công suất 5HP..."
    }
  ],
  "query": "Máy bơm có công suất bao nhiêu?"
}
```

### 5. Health Check

**Endpoint:** `GET /health`

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "OK",
  "service": "RAG System",
  "rag_ready": true,
  "data_dir": "./data",
  "db_dir": "./db"
}
```

## 📁 Cấu trúc Project

```
THITHI_python-api/
├── rag_main.py              # FastAPI application
├── rag_service.py            # RAG logic (PDF processing, embedding, QA)
├── requirements_rag.txt     # Dependencies
├── .env.example             # Template cho .env
├── .env                     # Environment variables (tạo từ .env.example)
├── data/                    # Thư mục chứa PDF files
│   ├── document1.pdf
│   ├── document2.pdf
│   └── ...
└── db/                      # ChromaDB storage (tự động tạo)
    ├── chroma.sqlite3
    └── ...
```

## 🔍 Chi tiết kỹ thuật

### PDF Processing

- Sử dụng `PyPDFDirectoryLoader` để load tất cả PDF trong thư mục
- Chia nhỏ bằng `RecursiveCharacterTextSplitter`:
  - `chunk_size`: 1000 ký tự
  - `chunk_overlap`: 100 ký tự (để giữ context)

### Embeddings

- Model: `text-embedding-004` (Google Gemini)
- Dimension: 768 (tự động)

### Vector Store

- ChromaDB lưu local tại `./db`
- Persist tự động sau khi ingest
- Tự động load lại khi restart server

### LLM

- Model: `gemini-1.5-flash`
- Temperature: 0.7
- Retrieval: Top 4 chunks liên quan nhất

## 🛠️ Cấu hình nâng cao

Chỉnh sửa file `.env`:

```env
# Thay đổi thư mục data
DATA_DIR=./my_pdfs

# Thay đổi thư mục database
DB_DIR=./my_db

# Điều chỉnh chunk size
CHUNK_SIZE=1500
CHUNK_OVERLAP=150

# Thay đổi port
PORT=8080
```

Hoặc chỉnh trực tiếp trong code `rag_main.py`:

```python
rag_service = RAGService(
    data_dir="./custom_data",
    db_dir="./custom_db",
    chunk_size=1500,
    chunk_overlap=150
)
```

## 📝 Ví dụ sử dụng với Python

```python
import requests

# 1. Ingest PDF files
response = requests.post("http://localhost:8000/ingest")
print(response.json())

# 2. Chat
response = requests.post(
    "http://localhost:8000/chat",
    json={"query": "Máy bơm có công suất bao nhiêu?"}
)
result = response.json()

print(f"Answer: {result['answer']}")
print(f"Sources: {result['sources']}")
```

## 🐛 Troubleshooting

### Lỗi: "GOOGLE_API_KEY không được tìm thấy"

**Giải pháp:**
- Kiểm tra file `.env` đã được tạo chưa
- Đảm bảo `GOOGLE_API_KEY=your_key` (không có dấu cách)
- Restart server sau khi thay đổi `.env`

### Lỗi: "Thư mục data không tồn tại"

**Giải pháp:**
- Tạo thư mục `data/` trong cùng thư mục với `rag_main.py`
- Hoặc chỉnh `DATA_DIR` trong `.env`

### Lỗi: "Chưa có dữ liệu. Hãy chạy /ingest trước"

**Giải pháp:**
- Chạy `POST /ingest` trước khi chat
- Đảm bảo có ít nhất 1 file PDF trong thư mục `data/`

### Lỗi khi load PDF

**Nguyên nhân có thể:**
- PDF bị corrupt
- PDF có password (chưa hỗ trợ)
- PDF là scan/hình ảnh (cần OCR)

**Giải pháp:**
- Kiểm tra PDF có thể mở được không
- Thử với PDF khác

### ChromaDB lỗi

**Giải pháp:**
- Xóa thư mục `db/` và chạy lại `/ingest`
- Kiểm tra quyền ghi vào thư mục `db/`

## 🔄 Workflow

1. **Setup:**
   ```bash
   pip install -r requirements_rag.txt
   cp .env.example .env
   # Chỉnh sửa .env với API key
   ```

2. **Chuẩn bị data:**
   ```bash
   mkdir data
   # Copy PDF files vào data/
   ```

3. **Khởi động server:**
   ```bash
   python rag_main.py
   ```

4. **Ingest documents:**
   ```bash
   curl -X POST http://localhost:8000/ingest
   ```

5. **Chat:**
   ```bash
   curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"query": "Câu hỏi của bạn"}'
   ```

## 📚 API Reference

### POST /ingest

Quét PDF và lưu vào ChromaDB.

**Response:**
- `status`: "success" | "warning" | "error"
- `message`: Thông báo
- `total_documents`: Số documents
- `total_chunks`: Số chunks
- `total_files`: Số files
- `files`: Danh sách tên files

### POST /chat

Chat với RAG system.

**Request:**
```json
{
  "query": "Câu hỏi"
}
```

**Response:**
```json
{
  "answer": "Câu trả lời",
  "sources": [
    {
      "file_name": "file.pdf",
      "page_number": 5,
      "content_preview": "..."
    }
  ],
  "query": "Câu hỏi gốc",
  "error": null
}
```

### GET /health

Health check.

**Response:**
```json
{
  "status": "OK",
  "service": "RAG System",
  "rag_ready": true,
  "data_dir": "./data",
  "db_dir": "./db"
}
```

## 🚀 Next Steps

- [ ] Thêm support cho PDF có password
- [ ] Thêm OCR cho PDF scan (Tesseract)
- [ ] Thêm support cho file Word, Excel
- [ ] Thêm authentication
- [ ] Thêm rate limiting
- [ ] Thêm logging chi tiết hơn
- [ ] Thêm metrics và monitoring

## 📄 License

MIT

## 👥 Contributors

Created for THITHI AI Project
