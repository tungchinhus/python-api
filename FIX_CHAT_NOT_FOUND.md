# Hướng Dẫn: Sửa Lỗi Chat AI Không Tìm Được Thông Tin

## 🔍 Vấn đề

Chat AI không tìm được thông tin trong database, có thể do:
1. **Tìm trong bảng sai**: RAG mặc định tìm trong `rag_documents`, nhưng dữ liệu có thể ở `TSMay` hoặc bảng khác
2. **Similarity threshold quá cao**: Chỉ lấy kết quả có độ tương đồng rất cao
3. **Chưa có embeddings**: Dữ liệu chưa được vectorize

## ✅ Giải pháp

### 1. Chỉ định bảng cụ thể khi chat

**Cách 1: Dùng parameter `table_name`**

```python
POST /chat
{
  "query": "có bao nhiêu tbkt",
  "table_name": "TSMay",  // ← Chỉ định bảng cụ thể
  "similarity_threshold": 0.3,  // ← Giảm threshold để tìm nhiều kết quả hơn
  "top_k": 10
}
```

**Cách 2: Tìm trong nhiều bảng**

```python
POST /chat
{
  "query": "có bao nhiêu tbkt",
  "search_multiple_tables": true,
  "table_names": ["TSMay", "rag_documents", "TSTN_1P_2021"],
  "similarity_threshold": 0.3,
  "top_k": 10
}
```

### 2. Kiểm tra dữ liệu trong database

**Kiểm tra bảng có dữ liệu không:**
```sql
-- Kiểm tra số lượng records
SELECT COUNT(*) FROM dbo.[TSMay];

-- Kiểm tra có embeddings không
SELECT COUNT(*) FROM dbo.[TSMay] WHERE Embedding IS NOT NULL;
SELECT COUNT(*) FROM dbo.[TSMay] WHERE VectorJson IS NOT NULL;

-- Kiểm tra có từ "TBKT" trong content không
SELECT TOP 10 ID, Content 
FROM dbo.[TSMay] 
WHERE Content LIKE '%TBKT%';
```

### 3. Kiểm tra embeddings

**Nếu chưa có embeddings, cần import lại:**
```bash
# Import Excel với embeddings
python excel_to_sql_vector.py --file "C:\MyData\projects\THITHI\Data\TSMay.xlsx" --table "TSMay"
```

### 4. Giảm similarity threshold

Nếu threshold quá cao (0.7-0.9), sẽ chỉ lấy kết quả rất khớp. Giảm xuống 0.3-0.5:

```python
POST /chat
{
  "query": "có bao nhiêu tbkt",
  "table_name": "TSMay",
  "similarity_threshold": 0.3,  // ← Giảm từ 0.5 xuống 0.3
  "top_k": 20  // ← Tăng số lượng kết quả
}
```

### 5. Sử dụng endpoint `/api/search/vector` (Python API)

Endpoint này đã hỗ trợ chỉ định bảng:

```python
POST http://localhost:5005/api/search/vector
{
  "query": "có bao nhiêu tbkt",
  "tableName": "TSMay",
  "topN": 10,
  "similarityThreshold": 0.3
}
```

## 🔧 Cấu hình mặc định

**File `.env`:**
```env
# Bảng mặc định cho RAG
RAG_TABLE_NAME=rag_documents

# Nếu muốn đổi mặc định sang TSMay
# RAG_TABLE_NAME=TSMay
```

## 📝 Ví dụ sử dụng

### Ví dụ 1: Chat với bảng TSMay

```python
import requests

url = "http://localhost:8000/chat"
payload = {
    "query": "có bao nhiêu tbkt",
    "table_name": "TSMay",
    "similarity_threshold": 0.3,
    "top_k": 10,
    "return_suggestions": True
}

response = requests.post(url, json=payload)
result = response.json()

print(f"Câu trả lời: {result['answer']}")
print(f"Số sources: {result.get('total_sources', 0)}")
```

### Ví dụ 2: Tìm trong nhiều bảng

```python
import requests

url = "http://localhost:8000/chat"
payload = {
    "query": "có bao nhiêu tbkt",
    "search_multiple_tables": True,
    "table_names": ["TSMay", "rag_documents"],
    "similarity_threshold": 0.3,
    "top_k": 10
}

response = requests.post(url, json=payload)
result = response.json()

print(f"Câu trả lời: {result['answer']}")
for source in result.get('sources', []):
    print(f"  - {source.get('table_name', 'unknown')}: {source.get('content_preview', '')[:100]}")
```

### Ví dụ 3: Dùng Python API endpoint

```python
import requests

url = "http://localhost:5005/api/search/vector"
payload = {
    "query": "có bao nhiêu tbkt",
    "tableName": "TSMay",
    "topN": 10,
    "similarityThreshold": 0.3
}

response = requests.post(url, json=payload)
result = response.json()

print(f"Tìm thấy {result.get('totalResults', 0)} kết quả:")
for r in result.get('results', []):
    print(f"  ID={r['id']}, Similarity={r['similarity']:.2%}")
    print(f"  Content: {r['content'][:200]}...")
```

## 🐛 Troubleshooting

### Vấn đề: "Bảng không tồn tại"

**Giải pháp:**
- Kiểm tra tên bảng trong SQL Server
- Đảm bảo tên bảng đúng (case-sensitive trong một số trường hợp)

### Vấn đề: "Không có Embedding hoặc VectorJson"

**Giải pháp:**
- Import lại dữ liệu với embeddings:
  ```bash
  python excel_to_sql_vector.py --file "path/to/file.xlsx" --table "TSMay"
  ```

### Vấn đề: "Không tìm thấy kết quả nào"

**Giải pháp:**
1. Giảm `similarity_threshold` xuống 0.2-0.3
2. Tăng `top_k` lên 20-50
3. Kiểm tra query có từ khóa trong database không:
   ```sql
   SELECT TOP 10 * FROM dbo.[TSMay] WHERE Content LIKE '%tbkt%';
   ```

### Vấn đề: "Kết quả không chính xác"

**Giải pháp:**
1. Tăng `similarity_threshold` lên 0.6-0.7
2. Làm rõ query: thêm context, từ khóa cụ thể hơn
3. Sử dụng suggestions để chọn kết quả phù hợp

## 📊 Kiểm tra nhanh

**Script kiểm tra:**
```python
import requests
import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

# 1. Kiểm tra bảng có tồn tại không
connection_string = os.getenv("SQL_CONNECTION_STRING")
conn = pyodbc.connect(connection_string)
cursor = conn.cursor()

tables = ["TSMay", "rag_documents"]
for table in tables:
    cursor.execute(f"""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = '{table}'
    """)
    exists = cursor.fetchone()[0] > 0
    print(f"Bảng {table}: {'✓ Tồn tại' if exists else '✗ Không tồn tại'}")
    
    if exists:
        cursor.execute(f"SELECT COUNT(*) FROM dbo.[{table}]")
        total = cursor.fetchone()[0]
        cursor.execute(f"SELECT COUNT(*) FROM dbo.[{table}] WHERE Embedding IS NOT NULL")
        with_embedding = cursor.fetchone()[0]
        cursor.execute(f"SELECT COUNT(*) FROM dbo.[{table}] WHERE VectorJson IS NOT NULL")
        with_vectorjson = cursor.fetchone()[0]
        
        print(f"  - Tổng số records: {total}")
        print(f"  - Có Embedding: {with_embedding}")
        print(f"  - Có VectorJson: {with_vectorjson}")

# 2. Test search
url = "http://localhost:8000/chat"
payload = {
    "query": "có bao nhiêu tbkt",
    "table_name": "TSMay",
    "similarity_threshold": 0.3,
    "top_k": 10
}

try:
    response = requests.post(url, json=payload, timeout=30)
    result = response.json()
    print(f"\nKết quả tìm kiếm:")
    print(f"  - Câu trả lời: {result.get('answer', 'N/A')[:100]}...")
    print(f"  - Số sources: {result.get('total_sources', 0)}")
except Exception as e:
    print(f"\nLỗi: {e}")
```

## 🎯 Tóm tắt

**Để Chat AI tìm được thông tin:**

1. ✅ **Chỉ định bảng đúng**: Dùng `table_name` parameter
2. ✅ **Giảm threshold**: `similarity_threshold: 0.3` thay vì 0.5
3. ✅ **Kiểm tra embeddings**: Đảm bảo dữ liệu đã được vectorize
4. ✅ **Tăng top_k**: Lấy nhiều kết quả hơn để tìm
5. ✅ **Tìm trong nhiều bảng**: Dùng `search_multiple_tables: true`
