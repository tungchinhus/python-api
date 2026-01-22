# Quick Start: Cấu Hình .env

## 🚀 Cách nhanh nhất

### Bước 1: Tạo file .env

**Cách 1: Dùng script (Windows)**
```bash
create_env.bat
```

**Cách 2: Copy thủ công**
```bash
copy env_template.txt .env
```

**Cách 3: Tạo mới**
Tạo file `.env` trong thư mục `THITHI_python-api` với nội dung:

```env
# Google API Key - BẮT BUỘC
GOOGLE_API_KEY=your_google_api_key_here

# SQL Server - BẮT BUỘC
SQL_SERVER=localhost
SQL_DATABASE=THITHI_AI
SQL_TRUSTED_CONNECTION=yes

# Các cấu hình khác (tùy chọn)
RAG_TABLE_NAME=rag_documents
DATA_DIR=./data
PYTHON_API_URL=http://localhost:5005/vectorize
USE_SQL_EMBEDDINGS=false
EMBEDDING_DIMENSION=768
CHUNK_SIZE=1000
CHUNK_OVERLAP=100
PORT=5005
```

### Bước 2: Lấy Google API Key

1. Truy cập: **https://aistudio.google.com/app/apikey**
2. Đăng nhập bằng Google account
3. Click **"Create API Key"**
4. Copy API key (dạng: `AIzaSy...`)
5. Mở file `.env` và thay thế `your_google_api_key_here` bằng API key thật

### Bước 3: Cấu hình SQL Server

**Nếu SQL Server trên cùng máy (Windows Authentication):**
```env
SQL_SERVER=localhost
SQL_DATABASE=THITHI_AI
SQL_TRUSTED_CONNECTION=yes
```

**Nếu SQL Server trên máy khác:**
```env
SQL_SERVER=192.168.1.100  # IP hoặc hostname
SQL_DATABASE=THITHI_AI
SQL_TRUSTED_CONNECTION=yes
```

**Nếu dùng SQL Authentication:**
```env
SQL_SERVER=localhost
SQL_DATABASE=THITHI_AI
SQL_TRUSTED_CONNECTION=no
SQL_USERNAME=your_username
SQL_PASSWORD=your_password
```

### Bước 4: Test cấu hình

```bash
# Test SQL connection
python test_sql_connection.py

# Test Google API
python test_google_api.py
```

## ✅ Checklist

- [ ] File `.env` đã được tạo
- [ ] `GOOGLE_API_KEY` đã được điền (không phải placeholder)
- [ ] SQL Server connection đã được cấu hình
- [ ] Đã test SQL connection thành công
- [ ] Đã test Google API thành công

## 📚 Xem thêm

- `HUONG_DAN_ENV.md` - Hướng dẫn chi tiết
- `START_SERVICES.md` - Khởi động services
- `env_template.txt` - Template file .env
