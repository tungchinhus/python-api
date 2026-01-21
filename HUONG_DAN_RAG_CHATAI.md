# Hướng dẫn: ChatAI hiểu và truy xuất thông tin từ rag_documents

## 📚 Tổng quan

Hệ thống RAG (Retrieval-Augmented Generation) cho phép ChatAI hiểu và trả lời câu hỏi dựa trên thông tin trong bảng `rag_documents` của SQL Server. Quá trình này hoạt động qua 3 bước chính:

1. **Ingest (Nhập liệu)**: Chuyển đổi tài liệu PDF thành embeddings và lưu vào database
2. **Retrieval (Truy xuất)**: Tìm kiếm các đoạn văn bản liên quan nhất với câu hỏi
3. **Generation (Tạo câu trả lời)**: Sử dụng LLM (Gemini) để tạo câu trả lời dựa trên context

---

## 🔄 Quy trình hoạt động chi tiết

### Bước 1: Ingest Documents (Nhập liệu)

Khi bạn chạy `POST /ingest`, hệ thống sẽ:

#### 1.1. Load PDF files
```python
# Quét tất cả file PDF trong thư mục ./data
loader = PyPDFDirectoryLoader(str(self.data_dir))
documents = loader.load()
```

#### 1.2. Chia nhỏ thành chunks
```python
# Chia mỗi document thành các đoạn nhỏ (chunks)
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,      # Mỗi chunk ~1000 ký tự
    chunk_overlap=100      # Overlap 100 ký tự giữa các chunks
)
chunks = text_splitter.split_documents(documents)
```

**Tại sao cần chia nhỏ?**
- LLM có giới hạn độ dài input
- Chia nhỏ giúp tìm kiếm chính xác hơn
- Overlap giúp không mất thông tin ở ranh giới

#### 1.3. Tạo Embeddings (Vector hóa)

Mỗi chunk được chuyển thành một **embedding vector** (mảng số thực):

```python
# Ví dụ: "Máy bơm có công suất 5HP"
# → Embedding: [-0.069, -0.024, 0.028, ..., 0.145] (384 số)
```

**Embedding là gì?**
- Là biểu diễn số học của văn bản
- Các văn bản có nghĩa tương tự sẽ có vector gần nhau
- Cho phép tìm kiếm theo ngữ nghĩa (semantic search)

**Có 2 cách tạo embeddings:**

**Option A: SQL Server AI_GENERATE_EMBEDDINGS**
```sql
SELECT AI_GENERATE_EMBEDDINGS(@text USE MODEL local_onnx_embeddings)
```
- Sử dụng ONNX model trong SQL Server
- Không cần Python API

**Option B: Python API**
```python
POST http://localhost:5005/vectorize
{
  "texts": ["Máy bơm có công suất 5HP"]
}
```
- Linh hoạt hơn, có thể dùng nhiều models

#### 1.4. Lưu vào SQL Server

```sql
INSERT INTO dbo.[rag_documents] 
(Content, VectorJson, Embedding, FileName, PageNumber, ChunkIndex)
VALUES 
('Máy bơm có công suất 5HP...', 
 '[-0.069, -0.024, ...]',  -- JSON backup
 CAST('[0.069, 0.024, ...]' AS VECTOR(384)),  -- Native VECTOR type
 'manual.pdf', 
 5, 
 12)
```

**Cấu trúc bảng:**
- `Content`: Văn bản gốc (NVARCHAR(MAX))
- `Embedding`: Vector embedding (VECTOR(384)) - SQL Server 2025
- `VectorJson`: Backup dạng JSON (NVARCHAR(MAX))
- `FileName`: Tên file nguồn
- `PageNumber`: Số trang trong PDF
- `ChunkIndex`: Thứ tự chunk

---

### Bước 2: Chat - Retrieval (Truy xuất)

Khi user hỏi: **"Máy bơm có công suất bao nhiêu?"**

#### 2.1. Generate embedding cho query

```python
# Chuyển câu hỏi thành vector
query = "Máy bơm có công suất bao nhiêu?"
query_vector = generate_embedding(query)
# → [-0.071, -0.025, 0.029, ..., 0.142]
```

#### 2.2. Vector Similarity Search

Hệ thống tìm các chunks có embedding **gần nhất** với query vector:

```sql
SELECT TOP (4)
    ID,
    Content,
    FileName,
    PageNumber,
    ChunkIndex,
    (1.0 - VECTOR_DISTANCE(
        Embedding, 
        CAST(@queryVector AS VECTOR(384)), 
        COSINE
    )) AS Similarity
FROM dbo.[rag_documents]
WHERE Embedding IS NOT NULL
ORDER BY VECTOR_DISTANCE(
    Embedding, 
    CAST(@queryVector AS VECTOR(384)), 
    COSINE
) ASC
```

**VECTOR_DISTANCE hoạt động như thế nào?**
- Tính khoảng cách giữa 2 vectors bằng **Cosine Similarity**
- Cosine Similarity = 1.0 → Giống nhau hoàn toàn
- Cosine Similarity = 0.0 → Khác nhau hoàn toàn
- ORDER BY ASC → Lấy những vector gần nhất (khoảng cách nhỏ nhất)

**Ví dụ kết quả:**
```
ID  | Content                          | Similarity | FileName
----|----------------------------------|------------|----------
19  | Máy bơm Model X có công suất 5HP | 0.92       | manual.pdf
23  | Thông số kỹ thuật máy bơm: 5HP   | 0.88       | manual.pdf
31  | Công suất: 5HP, điện áp: 220V    | 0.85       | spec.pdf
```

#### 2.3. Lấy Top-K chunks

Hệ thống lấy top 4 chunks có similarity cao nhất để làm context.

---

### Bước 3: Generation (Tạo câu trả lời)

#### 3.1. Tạo Prompt với Context

```python
context = """
[manual.pdf, trang 5]: Máy bơm Model X có công suất 5HP...
[manual.pdf, trang 6]: Thông số kỹ thuật máy bơm: 5HP...
[spec.pdf, trang 2]: Công suất: 5HP, điện áp: 220V...
"""

prompt = f"""Bạn là một trợ lý AI thông minh. Hãy trả lời câu hỏi dựa trên các đoạn văn bản được cung cấp bên dưới.

Context (các đoạn văn bản liên quan):
{context}

Câu hỏi: {query}

Hướng dẫn:
- Chỉ trả lời dựa trên thông tin có trong context
- Nếu không tìm thấy thông tin trong context, hãy nói rõ "Tôi không tìm thấy thông tin này trong tài liệu"
- Trả lời bằng tiếng Việt nếu câu hỏi là tiếng Việt
- Trả lời ngắn gọn, chính xác và dễ hiểu

Câu trả lời:"""
```

#### 3.2. Gọi LLM (Gemini)

```python
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=api_key,
    temperature=0.7
)

answer = llm.invoke(prompt)
```

**Gemini sẽ:**
- Đọc context từ các chunks liên quan
- Hiểu câu hỏi của user
- Tổng hợp thông tin và tạo câu trả lời
- Chỉ dựa vào context, không tự bịa đặt

#### 3.3. Trả về kết quả

```json
{
  "answer": "Theo tài liệu, máy bơm có công suất 5HP. Thông tin này được đề cập trong manual.pdf (trang 5) và spec.pdf (trang 2).",
  "sources": [
    {
      "file_name": "manual.pdf",
      "page_number": 5,
      "content_preview": "Máy bơm Model X có công suất 5HP..."
    },
    {
      "file_name": "spec.pdf",
      "page_number": 2,
      "content_preview": "Công suất: 5HP, điện áp: 220V..."
    }
  ],
  "query": "Máy bơm có công suất bao nhiêu?"
}
```

---

## 🎯 Tại sao RAG hiệu quả?

### 1. Semantic Search (Tìm kiếm ngữ nghĩa)

Không chỉ tìm kiếm từ khóa, mà hiểu **ý nghĩa**:

**Ví dụ:**
- Query: "Công suất máy bơm?"
- Tìm được: "Máy bơm Model X có công suất 5HP"
- Dù không có từ "công suất" trong query, nhưng embedding hiểu được nghĩa tương tự

### 2. Context-Aware (Nhận thức ngữ cảnh)

LLM nhận được **context cụ thể** từ database, không phải dựa vào training data cũ:

- ✅ Trả lời chính xác về thông tin trong tài liệu
- ✅ Có thể trả lời về thông tin mới nhất
- ✅ Không bịa đặt thông tin không có trong context

### 3. Traceable (Có thể truy vết)

Mỗi câu trả lời đều có **sources**:
- Biết được thông tin lấy từ file nào
- Biết được trang nào trong PDF
- Có thể kiểm tra lại nguồn gốc

---

## 🔌 Tích hợp với Frontend

### Cách 1: Gọi trực tiếp Python RAG API

```typescript
// Trong chat.service.ts
sendMessageToRAG(query: string): Observable<ChatResponse> {
  const headers = new HttpHeaders({
    'Content-Type': 'application/json'
  });

  return this.http.post<ChatResponse>(
    'http://localhost:8000/chat',
    { query },
    { headers }
  );
}
```

### Cách 2: Tích hợp vào Firebase Function

Có thể tạo Firebase Function wrapper để gọi Python RAG API:

```javascript
// functions/src/index.ts
export const chatFunction = functions.https.onRequest(async (req, res) => {
  const { query } = req.body;
  
  // Gọi Python RAG API
  const ragResponse = await axios.post('http://localhost:8000/chat', {
    query
  });
  
  // Trả về kết quả
  res.json({
    answer: ragResponse.data.answer,
    sources: ragResponse.data.sources
  });
});
```

---

## 📊 Ví dụ thực tế

### Scenario: User hỏi về "Chuyển đổi số"

**Query:** "FPT có những chương trình chuyển đổi số nào?"

**Bước 1: Generate embedding**
```
Query: "FPT có những chương trình chuyển đổi số nào?"
→ Vector: [-0.052, 0.031, -0.018, ..., 0.127]
```

**Bước 2: Vector Search**
```sql
-- Tìm top 4 chunks liên quan
SELECT TOP 4 Content, Similarity
FROM rag_documents
ORDER BY VECTOR_DISTANCE(...) ASC
```

**Kết quả:**
```
1. "Các chương trình hành động có thể được gi..." (Similarity: 0.91)
2. "FPT đề xuất dự kiến chi phí trên cơ sở ki..." (Similarity: 0.87)
3. "Thiết lập nhóm CĐS tại THIBIDI giúp làm r..." (Similarity: 0.84)
4. "Phương thức triển khai phù hợp với lộ trì..." (Similarity: 0.81)
```

**Bước 3: Generate Answer**
```
Context: [4 chunks liên quan về chuyển đổi số]

Answer: "Theo tài liệu, FPT có các chương trình chuyển đổi số bao gồm:
- Thiết lập nhóm CĐS tại THIBIDI
- Các chương trình hành động cụ thể
- Phương thức triển khai phù hợp với lộ trình

Thông tin chi tiết được đề cập trong các tài liệu nội bộ của FPT."
```

---

## 🛠️ Cấu hình và Tối ưu

### 1. Tăng độ chính xác

**Tăng số chunks (top_k):**
```python
result = service.chat(query, top_k=8)  # Thay vì 4
```

**Giảm chunk_size để chia nhỏ hơn:**
```python
rag_service = RAGServiceSQL(
    chunk_size=500,  # Thay vì 1000
    chunk_overlap=50
)
```

### 2. Tăng tốc độ

**Tạo Vector Index:**
```sql
CREATE VECTOR INDEX IX_rag_documents_Embedding 
ON dbo.[rag_documents] (Embedding) 
WITH (INDEX_TYPE = HNSW, DISTANCE_FUNCTION = COSINE);
```

**Giảm embedding dimension (nếu có thể):**
```python
embedding_dimension=256  # Thay vì 384 (nhanh hơn nhưng kém chính xác hơn)
```

### 3. Filter theo metadata

Có thể thêm filter để chỉ tìm trong một số files cụ thể:

```python
# Trong rag_service_sql.py, thêm parameter
def chat(self, query: str, top_k: int = 4, file_filter: List[str] = None):
    # ...
    if file_filter:
        sql += f" AND FileName IN ({','.join(['?' for _ in file_filter])})"
```

---

## 🐛 Troubleshooting

### Vấn đề: Không tìm thấy thông tin liên quan

**Nguyên nhân:**
- Embeddings chưa được tạo đúng
- Query không match với content trong database
- Chunk_size quá lớn, mất context

**Giải pháp:**
- Kiểm tra embeddings có NULL không: `SELECT COUNT(*) FROM rag_documents WHERE Embedding IS NULL`
- Thử query với từ khóa cụ thể hơn
- Giảm chunk_size và ingest lại

### Vấn đề: Câu trả lời không chính xác

**Nguyên nhân:**
- Top_k quá nhỏ, thiếu context
- LLM temperature quá cao (tự bịa đặt)

**Giải pháp:**
- Tăng top_k lên 6-8
- Giảm temperature xuống 0.3-0.5
- Kiểm tra similarity score (chỉ lấy > 0.7)

### Vấn đề: Tốc độ chậm

**Nguyên nhân:**
- Không có vector index
- Embedding dimension quá lớn
- Quá nhiều documents trong database

**Giải pháp:**
- Tạo vector index (HNSW)
- Giảm embedding dimension nếu có thể
- Thêm filter theo metadata để giảm số lượng documents cần search

---

## 📝 Tóm tắt

**ChatAI hiểu và truy xuất thông tin từ `rag_documents` qua 3 bước:**

1. **Ingest**: PDF → Chunks → Embeddings → SQL Server
2. **Retrieval**: Query → Embedding → Vector Search → Top-K chunks
3. **Generation**: Context + Query → LLM → Answer + Sources

**Điểm mạnh:**
- ✅ Semantic search (hiểu nghĩa, không chỉ từ khóa)
- ✅ Context-aware (dựa vào tài liệu cụ thể)
- ✅ Traceable (có sources để kiểm tra)

**Công nghệ sử dụng:**
- SQL Server 2025 VECTOR type
- VECTOR_DISTANCE function
- Google Gemini LLM
- LangChain framework

---

## 🔗 Tài liệu liên quan

- `README_RAG_SQL.md` - Hướng dẫn setup và sử dụng RAG API
- `rag_service_sql.py` - Implementation chi tiết
- `rag_main_sql.py` - FastAPI endpoints
- `CREATE_RAG_TABLE.sql` - Schema database
