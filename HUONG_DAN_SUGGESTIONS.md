# Hướng Dẫn: Tính Năng Suggestions (Gợi Ý) trong RAG Chat AI

## 📚 Tổng quan

Khi Chat AI tìm kiếm thông tin trong database, có thể có nhiều kết quả khớp với câu hỏi của bạn. Tính năng **Suggestions** cho phép:

1. **Hiển thị danh sách các kết quả khớp** với độ tương đồng (similarity) cao
2. **Cho phép bạn chọn** các kết quả cụ thể để xem chi tiết
3. **Tăng độ chính xác** của câu trả lời bằng cách chỉ sử dụng thông tin bạn quan tâm

---

## 🎯 Khi nào Suggestions xuất hiện?

Suggestions sẽ tự động xuất hiện khi:
- Có **ít nhất 3 kết quả** khớp với câu hỏi (similarity >= threshold)
- `return_suggestions=true` trong request (mặc định là `true`)
- Bạn chưa chọn suggestions cụ thể

---

## 🔌 API Endpoints

### 1. Chat với Suggestions (Tự động)

**Endpoint:** `POST /chat`

**Request:**
```json
{
  "query": "Máy bơm có công suất bao nhiêu?",
  "top_k": 4,
  "similarity_threshold": 0.5,
  "return_suggestions": true
}
```

**Response (khi có nhiều kết quả khớp):**
```json
{
  "answer": "Theo tài liệu, máy bơm có công suất 5HP...",
  "sources": [
    {
      "id": 19,
      "file_name": "manual.pdf",
      "page_number": 5,
      "content_preview": "Máy bơm Model X có công suất 5HP...",
      "similarity": 0.92
    },
    {
      "id": 23,
      "file_name": "manual.pdf",
      "page_number": 6,
      "content_preview": "Thông số kỹ thuật máy bơm: 5HP...",
      "similarity": 0.88
    }
  ],
  "query": "Máy bơm có công suất bao nhiêu?",
  "suggestions": {
    "has_suggestions": true,
    "total_available": 8,
    "suggestions": [
      {
        "index": 1,
        "id": 19,
        "content_preview": "Máy bơm Model X có công suất 5HP, điện áp 220V...",
        "file_name": "manual.pdf",
        "page_number": 5,
        "similarity": 0.92,
        "similarity_percent": 92.0
      },
      {
        "index": 2,
        "id": 23,
        "content_preview": "Thông số kỹ thuật máy bơm: 5HP, lưu lượng...",
        "file_name": "manual.pdf",
        "page_number": 6,
        "similarity": 0.88,
        "similarity_percent": 88.0
      },
      {
        "index": 3,
        "id": 31,
        "content_preview": "Công suất: 5HP, điện áp: 220V, tần số...",
        "file_name": "spec.pdf",
        "page_number": 2,
        "similarity": 0.85,
        "similarity_percent": 85.0
      }
    ],
    "message": "Tìm thấy 8 kết quả khớp. Bạn có thể chọn các kết quả cụ thể để xem chi tiết."
  },
  "total_sources": 2
}
```

---

### 2. Lấy danh sách Suggestions (Trước khi chat)

**Endpoint:** `POST /chat/suggestions`

**Request:**
```json
{
  "query": "Máy bơm có công suất bao nhiêu?",
  "top_k": 10,
  "similarity_threshold": 0.5,
  "min_suggestions": 2
}
```

**Response:**
```json
{
  "query": "Máy bơm có công suất bao nhiêu?",
  "suggestions": [
    {
      "index": 1,
      "id": 19,
      "content_preview": "Máy bơm Model X có công suất 5HP...",
      "file_name": "manual.pdf",
      "page_number": 5,
      "similarity": 0.92,
      "similarity_percent": 92.0
    },
    {
      "index": 2,
      "id": 23,
      "content_preview": "Thông số kỹ thuật máy bơm: 5HP...",
      "file_name": "manual.pdf",
      "page_number": 6,
      "similarity": 0.88,
      "similarity_percent": 88.0
    }
  ],
  "total_found": 8,
  "has_multiple_suggestions": true,
  "similarity_threshold": 0.5,
  "message": "Tìm thấy 8 kết quả khớp"
}
```

---

### 3. Chat với Suggestions đã chọn

**Endpoint:** `POST /chat`

**Request:**
```json
{
  "query": "Máy bơm có công suất bao nhiêu?",
  "top_k": 4,
  "similarity_threshold": 0.5,
  "return_suggestions": false,
  "selected_suggestion_ids": [19, 23]
}
```

**Response:**
```json
{
  "answer": "Theo tài liệu manual.pdf, máy bơm Model X có công suất 5HP...",
  "sources": [
    {
      "id": 19,
      "file_name": "manual.pdf",
      "page_number": 5,
      "content_preview": "Máy bơm Model X có công suất 5HP...",
      "similarity": 0.92
    },
    {
      "id": 23,
      "file_name": "manual.pdf",
      "page_number": 6,
      "content_preview": "Thông số kỹ thuật máy bơm: 5HP...",
      "similarity": 0.88
    }
  ],
  "query": "Máy bơm có công suất bao nhiêu?",
  "suggestions": null,
  "total_sources": 2
}
```

---

## 💻 Ví dụ sử dụng với Python

### Ví dụ 1: Chat bình thường (tự động suggestions)

```python
import requests

url = "http://localhost:8000/chat"
payload = {
    "query": "FPT có những chương trình chuyển đổi số nào?",
    "top_k": 4,
    "similarity_threshold": 0.5,
    "return_suggestions": True
}

response = requests.post(url, json=payload)
result = response.json()

print(f"Câu trả lời: {result['answer']}")
print(f"\nSố sources: {result['total_sources']}")

# Kiểm tra có suggestions không
if result.get('suggestions') and result['suggestions']['has_suggestions']:
    print(f"\n📋 Tìm thấy {result['suggestions']['total_available']} kết quả khớp:")
    for suggestion in result['suggestions']['suggestions']:
        print(f"  [{suggestion['index']}] ID={suggestion['id']}, "
              f"Similarity={suggestion['similarity_percent']}%, "
              f"File={suggestion['file_name']}, Page={suggestion['page_number']}")
        print(f"      Preview: {suggestion['content_preview'][:100]}...")
```

### Ví dụ 2: Lấy suggestions trước, sau đó chọn

```python
import requests

# Bước 1: Lấy suggestions
url_suggestions = "http://localhost:8000/chat/suggestions"
payload = {
    "query": "FPT có những chương trình chuyển đổi số nào?",
    "top_k": 10,
    "similarity_threshold": 0.5
}

response = requests.post(url_suggestions, json=payload)
suggestions_result = response.json()

print(f"Tìm thấy {suggestions_result['total_found']} kết quả:")
for suggestion in suggestions_result['suggestions']:
    print(f"  [{suggestion['index']}] ID={suggestion['id']}, "
          f"Similarity={suggestion['similarity_percent']}%")
    print(f"      {suggestion['content_preview'][:150]}...")
    print()

# Bước 2: User chọn suggestions (ví dụ: chọn 2 suggestions đầu tiên)
selected_ids = [s['id'] for s in suggestions_result['suggestions'][:2]]

# Bước 3: Chat với suggestions đã chọn
url_chat = "http://localhost:8000/chat"
payload_chat = {
    "query": "FPT có những chương trình chuyển đổi số nào?",
    "selected_suggestion_ids": selected_ids,
    "return_suggestions": False
}

response_chat = requests.post(url_chat, json=payload_chat)
chat_result = response_chat.json()

print(f"\nCâu trả lời (dựa trên {len(selected_ids)} suggestions đã chọn):")
print(chat_result['answer'])
```

### Ví dụ 3: Tích hợp vào Frontend (JavaScript/TypeScript)

```typescript
// 1. Gửi query và nhận suggestions
async function getChatWithSuggestions(query: string) {
  const response = await fetch('http://localhost:8000/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: query,
      return_suggestions: true,
      similarity_threshold: 0.5
    })
  });
  
  const result = await response.json();
  
  // Hiển thị câu trả lời
  displayAnswer(result.answer);
  
  // Hiển thị suggestions nếu có
  if (result.suggestions?.has_suggestions) {
    displaySuggestions(result.suggestions.suggestions);
  }
  
  return result;
}

// 2. Hiển thị suggestions cho user chọn
function displaySuggestions(suggestions: any[]) {
  const suggestionsContainer = document.getElementById('suggestions');
  suggestionsContainer.innerHTML = '<h3>Kết quả khớp (chọn để xem chi tiết):</h3>';
  
  suggestions.forEach(suggestion => {
    const suggestionDiv = document.createElement('div');
    suggestionDiv.className = 'suggestion-item';
    suggestionDiv.innerHTML = `
      <input type="checkbox" value="${suggestion.id}" id="sug-${suggestion.id}">
      <label for="sug-${suggestion.id}">
        <strong>[${suggestion.index}]</strong> 
        Similarity: ${suggestion.similarity_percent}% | 
        File: ${suggestion.file_name}, Page: ${suggestion.page_number}
        <p>${suggestion.content_preview}</p>
      </label>
    `;
    suggestionsContainer.appendChild(suggestionDiv);
  });
  
  // Thêm nút "Xem chi tiết với các suggestions đã chọn"
  const button = document.createElement('button');
  button.textContent = 'Xem chi tiết với các kết quả đã chọn';
  button.onclick = () => {
    const selectedIds = Array.from(document.querySelectorAll('input[type="checkbox"]:checked'))
      .map((cb: any) => parseInt(cb.value));
    
    if (selectedIds.length > 0) {
      getChatWithSelectedSuggestions(query, selectedIds);
    }
  };
  suggestionsContainer.appendChild(button);
}

// 3. Chat với suggestions đã chọn
async function getChatWithSelectedSuggestions(query: string, selectedIds: number[]) {
  const response = await fetch('http://localhost:8000/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: query,
      selected_suggestion_ids: selectedIds,
      return_suggestions: false
    })
  });
  
  const result = await response.json();
  displayAnswer(result.answer);
  displaySources(result.sources);
}
```

---

## ⚙️ Cấu hình

### Parameters

| Parameter | Type | Default | Mô tả |
|-----------|------|---------|-------|
| `query` | string | required | Câu hỏi của user |
| `top_k` | int | 4 | Số lượng kết quả tối đa để lấy |
| `similarity_threshold` | float | 0.5 | Ngưỡng similarity tối thiểu (0.0 - 1.0) |
| `return_suggestions` | bool | true | Có trả về suggestions không |
| `selected_suggestion_ids` | List[int] | null | Danh sách ID của suggestions được chọn |
| `min_suggestions` | int | 2 | Số lượng suggestions tối thiểu để hiển thị |

### Tuning Suggestions

**Tăng số lượng suggestions:**
```json
{
  "query": "...",
  "top_k": 10,  // Tăng từ 4 lên 10
  "similarity_threshold": 0.4  // Giảm threshold để lấy nhiều kết quả hơn
}
```

**Tăng độ chính xác (chỉ lấy kết quả rất khớp):**
```json
{
  "query": "...",
  "similarity_threshold": 0.7  // Tăng threshold lên 0.7
}
```

---

## 🎨 UI/UX Best Practices

### 1. Hiển thị Suggestions

- **Dạng danh sách có checkbox** để user chọn nhiều suggestions
- **Hiển thị similarity score** (ví dụ: 92% khớp) để user biết độ liên quan
- **Preview nội dung** (200-300 ký tự đầu) để user quyết định
- **Hiển thị metadata**: file name, page number

### 2. Flow tương tác

```
User gửi query
    ↓
Hiển thị câu trả lời + suggestions (nếu có)
    ↓
User chọn suggestions (nếu muốn)
    ↓
Gửi lại query với selected_suggestion_ids
    ↓
Hiển thị câu trả lời chi tiết hơn
```

### 3. Visual Design

- **Highlight suggestions** với similarity cao (> 0.8) bằng màu xanh
- **Suggestions trung bình** (0.5 - 0.8) bằng màu vàng
- **Hiển thị số lượng** suggestions: "Tìm thấy 8 kết quả khớp"

---

## 🔍 Troubleshooting

### Vấn đề: Không có suggestions xuất hiện

**Nguyên nhân:**
- Có ít hơn 3 kết quả khớp
- `similarity_threshold` quá cao
- `return_suggestions=false`

**Giải pháp:**
- Giảm `similarity_threshold` xuống 0.3-0.4
- Tăng `top_k` lên 10-20
- Đảm bảo `return_suggestions=true`

### Vấn đề: Suggestions không chính xác

**Nguyên nhân:**
- Embeddings chưa được tạo đúng
- Query không rõ ràng

**Giải pháp:**
- Kiểm tra embeddings: `SELECT COUNT(*) FROM rag_documents WHERE Embedding IS NOT NULL`
- Làm rõ query: thêm context, từ khóa cụ thể hơn
- Tăng `similarity_threshold` lên 0.6-0.7

---

## 📝 Tóm tắt

**Tính năng Suggestions cho phép:**

1. ✅ **Tự động phát hiện** khi có nhiều kết quả khớp
2. ✅ **Hiển thị danh sách** các kết quả với similarity score
3. ✅ **Cho phép user chọn** suggestions cụ thể
4. ✅ **Tăng độ chính xác** bằng cách chỉ dùng thông tin được chọn
5. ✅ **Tương tác linh hoạt** với 2 endpoints: `/chat` và `/chat/suggestions`

**Workflow:**
```
Query → Search → Suggestions (nếu có) → User chọn → Answer với context đã chọn
```

---

## 🔗 Tài liệu liên quan

- `HUONG_DAN_RAG_CHATAI.md` - Hướng dẫn RAG cơ bản
- `rag_service_sql.py` - Implementation chi tiết
- `rag_main_sql.py` - FastAPI endpoints
