# Fix YAML Module Error

## Vấn đề
Python API không khởi động được với lỗi: `ModuleNotFoundError: No module named 'yaml'`

## Nguyên nhân
Module `PyYAML` (package name là `yaml` khi import) thiếu trong virtual environment, mặc dù `huggingface_hub` cần nó.

## Giải pháp đã áp dụng

1. ✅ Đã thêm `PyYAML>=6.0` vào `requirements.txt`
2. ✅ Đã cài đặt PyYAML vào virtual environment

## Cách khởi động lại Python API

```batch
cd d:\Project\thibidi\THITHI\python-api
start-service.bat
```

Hoặc thủ công:

```batch
cd d:\Project\thibidi\THITHI\python-api
venv\Scripts\activate.bat
python app.py
```

## Kiểm tra

Sau khi khởi động, kiểm tra health endpoint:

```powershell
Invoke-WebRequest -Uri "http://localhost:5005/health" -UseBasicParsing
```

Kết quả mong đợi:
```json
{
  "status": "OK",
  "service": "Python Vectorize API",
  "model_loaded": true
}
```

## Lưu ý

- Lần đầu tiên chạy, model embedding sẽ được download tự động (có thể mất vài phút)
- Model: `paraphrase-multilingual-MiniLM-L12-v2` (hỗ trợ tiếng Việt)
- Kích thước model: ~420 MB
