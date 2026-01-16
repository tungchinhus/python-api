# Python Vectorize API

API server để vectorize text thành embeddings, sử dụng sentence-transformers.

## Cài đặt

### 1. Tạo virtual environment (khuyến nghị)

```bash
cd THITHI_python-api
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

**Lưu ý:** Lần đầu cài đặt sẽ download model `paraphrase-multilingual-MiniLM-L12-v2` (khoảng 400MB), có thể mất vài phút.

### 3. Chạy server

```bash
python app.py
```

Server sẽ chạy tại: `http://localhost:5005`

## API Endpoints

### POST `/vectorize`

Vectorize text thành embeddings.

**Request:**
```json
{
  "texts": [
    "Máy Bơm - Model X - Công suất 5HP",
    "Máy Nén - Model Y - Công suất 10HP"
  ]
}
```

**Response:**
```json
{
  "vectors": [
    [0.1, 0.2, 0.3, ...],
    [0.4, 0.5, 0.6, ...]
  ],
  "count": 2,
  "dimension": 384
}
```

### GET `/health`

Kiểm tra service hoạt động.

**Response:**
```json
{
  "status": "OK",
  "service": "Python Vectorize API",
  "model_loaded": true
}
```

## Model sử dụng

- **Model:** `paraphrase-multilingual-MiniLM-L12-v2`
- **Dimension:** 384
- **Hỗ trợ:** 50+ ngôn ngữ bao gồm tiếng Việt
- **Size:** ~400MB (download tự động lần đầu)

## Troubleshooting

### Lỗi: "Model chưa được load"

- Kiểm tra logs để xem lỗi chi tiết
- Đảm bảo đã cài đặt đầy đủ dependencies: `pip install -r requirements.txt`
- Model sẽ tự động download lần đầu, đảm bảo có kết nối internet

### Lỗi: "Port 5005 already in use"

- Tìm process đang dùng port: `netstat -ano | findstr :5005`
- Kill process hoặc đổi port trong `app.py`

### Performance

- Model sẽ load vào memory lần đầu (mất vài giây)
- Vectorize batch sẽ nhanh hơn từng text một
- Với file lớn (>1000 texts), nên chia nhỏ thành batches

## Tùy chỉnh

### Đổi model khác

Trong `app.py`, thay đổi:
```python
model = SentenceTransformer('tên-model-khác')
```

Một số model phổ biến:
- `paraphrase-multilingual-MiniLM-L12-v2` - Hỗ trợ đa ngôn ngữ, nhẹ (384 dim)
- `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` - Tốt hơn nhưng nặng hơn (768 dim)
- `keepitreal/vietnamese-sbert` - Tối ưu cho tiếng Việt

### Đổi port

Trong `app.py`, thay đổi:
```python
app.run(host='0.0.0.0', port=5006, debug=True)
```

Và cập nhật `appsettings.json` trong .NET backend:
```json
{
  "PythonApi": {
    "VectorizeUrl": "http://localhost:5006/vectorize"
  }
}
```
