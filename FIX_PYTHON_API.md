# Hướng Dẫn Fix Lỗi Python API - ImportError cached_download

## Vấn đề
Python API không chạy được do lỗi:
```
ImportError: cannot import name 'cached_download' from 'huggingface_hub'
```

## Nguyên nhân
Version `sentence-transformers==2.2.2` không tương thích với `huggingface_hub` mới. Function `cached_download` đã bị deprecated/removed.

## Cách Fix

### Bước 1: Activate virtual environment
```bash
cd C:\MyData\projects\THITHI\THITHI_python-api
venv\Scripts\activate
```

### Bước 2: Update dependencies
```bash
pip install --upgrade sentence-transformers huggingface_hub
```

Hoặc cài đặt lại từ requirements.txt đã được update:
```bash
pip install -r requirements.txt --upgrade
```

### Bước 3: Verify installation
```bash
python -c "from sentence_transformers import SentenceTransformer; print('OK')"
```

### Bước 4: Restart Python API
```bash
python app.py
```

Hoặc dùng script:
```bash
run-server.bat
```

## Kiểm tra
1. Mở browser: http://localhost:5005/health
2. Phải trả về: `{"status": "OK", "service": "Python Vectorize API", "model_loaded": true}`

## Lưu ý
- Nếu vẫn lỗi, thử xóa và tạo lại virtual environment:
  ```bash
  rmdir /s venv
  python -m venv venv
  venv\Scripts\activate
  pip install -r requirements.txt
  ```
