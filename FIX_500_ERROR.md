# Hướng Dẫn: Sửa Lỗi 500 Internal Server Error

## 🔍 Vấn đề

Python API trả về lỗi **500 Internal Server Error** khi gọi endpoint `/api/search/vector`.

## ✅ Giải pháp

### Bước 1: Chạy script debug

```bash
python debug_api.py
```

Script này sẽ kiểm tra:
- ✅ Model embedding có load được không
- ✅ SQL Server connection có hoạt động không
- ✅ Logic vector search có lỗi không

### Bước 2: Kiểm tra logs

Khi chạy Python API, xem logs để biết lỗi cụ thể:

```bash
python app.py
```

Các lỗi phổ biến:

#### Lỗi 1: Model chưa load

**Triệu chứng:**
```
Lỗi khi load model: ...
Model is None
```

**Giải pháp:**
```bash
# Cài đặt lại sentence-transformers
pip install sentence-transformers

# Hoặc cài đặt tất cả dependencies
pip install -r requirements.txt
```

#### Lỗi 2: SQL Connection failed

**Triệu chứng:**
```
SQL connection error: ...
Cannot connect to SQL Server
```

**Giải pháp:**
1. Kiểm tra SQL Server đang chạy
2. Kiểm tra file `.env` có cấu hình đúng không
3. Test connection:
   ```bash
   python test_sql_connection.py
   ```

#### Lỗi 3: Table không tồn tại

**Triệu chứng:**
```
Table 'TSMay' does not exist
```

**Giải pháp:**
1. Kiểm tra tên bảng đúng chưa
2. Tạo bảng hoặc import dữ liệu:
   ```bash
   python excel_to_sql_vector.py --file "path/to/file.xlsx" --table "TSMay"
   ```

#### Lỗi 4: Không có Embedding column

**Triệu chứng:**
```
Table has no Embedding or VectorJson column
```

**Giải pháp:**
1. Import lại dữ liệu với embeddings:
   ```bash
   python excel_to_sql_vector.py --file "path/to/file.xlsx" --table "TSMay"
   ```

#### Lỗi 5: VECTOR_DISTANCE syntax error

**Triệu chứng:**
```
Invalid syntax in VECTOR_DISTANCE
```

**Giải pháp:**
1. Kiểm tra SQL Server version (cần 2025+)
2. Nếu không có VECTOR type, dùng VectorJson:
   ```sql
   -- Kiểm tra version
   SELECT @@VERSION
   ```

### Bước 3: Bật debug mode

Thêm vào file `.env`:
```env
DEBUG=true
```

Sau đó restart Python API để xem error traceback chi tiết.

### Bước 4: Kiểm tra từng component

#### Test Model:
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-mpnet-base-v2')
embedding = model.encode(["test"])
print(f"OK: {len(embedding[0])} dimensions")
```

#### Test SQL:
```bash
python test_sql_connection.py
```

#### Test Vector Search:
```bash
python debug_api.py
```

## 🔧 Quick Fixes

### Fix 1: Restart với debug

```bash
# Stop API hiện tại (Ctrl+C)
# Chạy lại với debug
python app.py
```

### Fix 2: Kiểm tra .env

```bash
# Đảm bảo có các biến:
# - SQL_SERVER hoặc SQL_CONNECTION_STRING
# - SQL_DATABASE
# - SQL_TRUSTED_CONNECTION hoặc SQL_USERNAME/SQL_PASSWORD
```

### Fix 3: Reinstall dependencies

```bash
pip install --upgrade sentence-transformers flask flask-cors pyodbc python-dotenv numpy
```

### Fix 4: Clear model cache

```bash
# Xóa cache model (nếu model bị corrupt)
# Model sẽ tự động download lại
rm -r ~/.cache/torch/sentence_transformers
# Hoặc trên Windows:
# Xóa thư mục: C:\Users\<username>\.cache\torch\sentence_transformers
```

## 📊 Diagnostic Checklist

Chạy các lệnh sau để kiểm tra:

```bash
# 1. Check model
python -c "from sentence_transformers import SentenceTransformer; m = SentenceTransformer('all-mpnet-base-v2'); print('OK')"

# 2. Check SQL
python test_sql_connection.py

# 3. Check Google API
python test_google_api.py

# 4. Full debug
python debug_api.py

# 5. Check services
python check_services.py
```

## 🎯 Common Solutions

### Solution 1: Model Loading Issue

**Nếu model không load:**
```python
# Thử load với explicit device
model = SentenceTransformer('all-mpnet-base-v2', device='cpu')
```

### Solution 2: SQL Connection Timeout

**Nếu connection timeout:**
```env
# Thêm timeout vào connection string
SQL_CONNECTION_STRING=...;Connection Timeout=30;
```

### Solution 3: Memory Issue

**Nếu hết RAM khi load model:**
```python
# Load model với device='cpu' và low_mem=True
model = SentenceTransformer('all-mpnet-base-v2', device='cpu')
```

## 📝 Log Analysis

Khi gặp lỗi 500, xem logs để tìm:

1. **Error message**: Dòng đầu tiên của error
2. **Traceback**: Stack trace để biết lỗi ở đâu
3. **Request details**: Query, table name, parameters

**Ví dụ log:**
```
❌ Error in vector search: division by zero
❌ Traceback:
  File "app.py", line 195, in search_vector
    query_embedding = model.encode([query])
  ...
```

## 🔗 Tài liệu liên quan

- `debug_api.py` - Script debug chi tiết
- `test_sql_connection.py` - Test SQL connection
- `START_SERVICES.md` - Hướng dẫn khởi động services
- `HUONG_DAN_ENV.md` - Cấu hình .env

## 💡 Tips

1. **Luôn check logs trước**: Logs sẽ cho biết lỗi cụ thể
2. **Chạy debug_api.py**: Script này sẽ tìm ra vấn đề
3. **Test từng component**: Model → SQL → Search logic
4. **Bật DEBUG mode**: Để xem error traceback đầy đủ
5. **Check .env file**: Đảm bảo cấu hình đúng
