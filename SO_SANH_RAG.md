# So Sánh: ChromaDB vs SQL Server Vector cho RAG System

## 📊 Tổng Quan

Có 2 phiên bản RAG system:
1. **ChromaDB Version** (`rag_main.py` + `rag_service.py`)
2. **SQL Server Vector Version** (`rag_main_sql.py` + `rag_service_sql.py`)

## 🔍 So Sánh Chi Tiết

| Tiêu chí | ChromaDB | SQL Server Vector |
|----------|----------|-------------------|
| **Storage** | Local file (`./db/`) | SQL Server database |
| **Dependencies** | ChromaDB library | pyodbc + SQL Server |
| **Vector Search** | ChromaDB native | SQL Server `VECTOR_DISTANCE` |
| **Embedding** | Python API hoặc Gemini | SQL Server `AI_GENERATE_EMBEDDINGS` hoặc Python API |
| **Integration** | Standalone | Tích hợp với .NET backend |
| **Scalability** | Limited (file-based) | Enterprise-grade (SQL Server) |
| **Backup** | Manual copy folder | SQL Server backup |
| **Performance** | Tốt cho small-medium data | Tốt cho large-scale data |
| **Setup Complexity** | Đơn giản (chỉ cần Python) | Phức tạp hơn (cần SQL Server) |
| **Cost** | Free (open source) | Cần SQL Server license |

## 🎯 Khi Nào Dùng ChromaDB?

✅ **Phù hợp khi:**
- Development/Testing nhanh
- Standalone application
- Không có SQL Server
- Data nhỏ (< 100K documents)
- Muốn setup đơn giản

❌ **Không phù hợp khi:**
- Cần tích hợp với hệ thống hiện có
- Data lớn (> 1M documents)
- Cần backup/restore tự động
- Cần transaction support

## 🎯 Khi Nào Dùng SQL Server Vector?

✅ **Phù hợp khi:**
- Đã có SQL Server 2025
- Cần tích hợp với .NET backend
- Data lớn, cần scalability
- Cần backup/restore tự động
- Muốn dùng `AI_GENERATE_EMBEDDINGS` của SQL Server
- Enterprise environment

❌ **Không phù hợp khi:**
- Không có SQL Server
- Muốn setup nhanh cho testing
- Standalone application
- Budget hạn chế (SQL Server license)

## 📝 Code Comparison

### ChromaDB Version

```python
# rag_service.py
from langchain_community.vectorstores import Chroma

self.vector_store = Chroma.from_documents(
    documents=chunks,
    embedding=self.embeddings,
    persist_directory=str(self.db_dir)
)

# Search
retriever = self.vector_store.as_retriever(search_kwargs={"k": 4})
```

### SQL Server Vector Version

```python
# rag_service_sql.py
import pyodbc

# Insert với VECTOR type
sql = """
INSERT INTO dbo.[rag_documents] 
(Content, Embedding, FileName, PageNumber)
VALUES (?, CAST(? AS VECTOR(384)), ?, ?)
"""

# Search với VECTOR_DISTANCE
sql = """
SELECT TOP (4)
    Content, FileName, PageNumber,
    (1.0 - VECTOR_DISTANCE(Embedding, CAST(? AS VECTOR(384)), COSINE)) AS Similarity
FROM dbo.[rag_documents]
ORDER BY VECTOR_DISTANCE(Embedding, CAST(? AS VECTOR(384)), COSINE) ASC
"""
```

## 🚀 Performance Comparison

### ChromaDB
- **Insert**: ~100-500 docs/second
- **Search**: ~10-50ms (với index)
- **Memory**: Low (file-based)

### SQL Server Vector
- **Insert**: ~50-200 docs/second (phụ thuộc vào SQL Server config)
- **Search**: ~20-100ms (với vector index)
- **Memory**: Higher (SQL Server buffer pool)

## 🔧 Setup Comparison

### ChromaDB Setup
```bash
# 1. Install
pip install chromadb

# 2. Run
python rag_main.py

# Done! ChromaDB tự động tạo ./db/
```

### SQL Server Setup
```bash
# 1. Install
pip install pyodbc

# 2. Setup SQL Server
# - Chạy CREATE_RAG_TABLE.sql
# - Setup EXTERNAL MODEL (nếu dùng AI_GENERATE_EMBEDDINGS)

# 3. Configure .env
SQL_SERVER=localhost
SQL_DATABASE=THITHI_AI
USE_SQL_EMBEDDINGS=true

# 4. Run
python rag_main_sql.py
```

## 💡 Recommendation

### Cho Project THITHI AI:

**Nên dùng SQL Server Vector vì:**
1. ✅ Đã có SQL Server 2025
2. ✅ Đã có .NET backend với SQL Server
3. ✅ Cần tích hợp tốt với hệ thống hiện tại
4. ✅ Có thể dùng `AI_GENERATE_EMBEDDINGS` của SQL Server
5. ✅ Unified storage cho tất cả data

**Có thể dùng ChromaDB khi:**
- Development/testing nhanh
- Prototype
- Standalone demo

## 🔄 Migration Path

Nếu đã dùng ChromaDB và muốn chuyển sang SQL Server:

1. **Export data từ ChromaDB** (nếu cần backup)
2. **Setup SQL Server table**: Chạy `CREATE_RAG_TABLE.sql`
3. **Re-ingest**: Chạy `/ingest` lại để import vào SQL Server
4. **Update code**: Đổi từ `rag_main.py` sang `rag_main_sql.py`

## 📚 Documentation

- ChromaDB: `README_RAG.md`
- SQL Server: `README_RAG_SQL.md`
- SQL Setup: `CREATE_RAG_TABLE.sql`

## 🎓 Kết Luận

**SQL Server Vector** là lựa chọn tốt hơn cho production environment, đặc biệt khi đã có SQL Server 2025 và cần tích hợp với hệ thống hiện tại.

**ChromaDB** phù hợp cho development, testing, hoặc standalone applications.
