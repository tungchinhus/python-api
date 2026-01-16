# Hướng dẫn Start Python API

## Cách 1: Dùng script tự động (Khuyến nghị)

```bash
cd python-api
start-simple.bat
```

Hoặc:

```bash
cd python-api
start.bat
```

## Cách 2: Start thủ công

```bash
cd python-api
venv\Scripts\activate
python app.py
```

## Kiểm tra Python API đã chạy

Mở trình duyệt hoặc dùng curl:

```bash
curl http://localhost:5005/health
```

Hoặc PowerShell:

```powershell
Invoke-WebRequest -Uri http://localhost:5005/health -UseBasicParsing
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

1. **Lần đầu chạy**: Model embedding sẽ được download tự động, có thể mất 5-10 phút tùy tốc độ internet.

2. **Port 5005**: Đảm bảo port 5005 không bị chiếm bởi ứng dụng khác.

3. **Virtual Environment**: Script sẽ tự động kích hoạt virtual environment. Nếu chưa có, chạy:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Kiểm tra log**: Khi start, bạn sẽ thấy:
   ```
   Đang load model embedding...
   Model đã load thành công!
   Starting Python Vectorize API on port 5005...
   ```

## Troubleshooting

### Lỗi: "No connection could be made"
- Kiểm tra Python API đã start chưa
- Kiểm tra port 5005 có bị chiếm không: `netstat -ano | findstr :5005`

### Lỗi: "Model download failed"
- Kiểm tra kết nối internet
- Model sẽ được lưu tại: `C:\Users\<username>\.cache\huggingface\`

### Lỗi: "Module not found"
- Đảm bảo đã activate virtual environment
- Chạy: `pip install -r requirements.txt`
