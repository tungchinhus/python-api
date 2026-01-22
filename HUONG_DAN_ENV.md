# Hướng Dẫn: Cấu Hình File .env

## 📝 Tổng quan

File `.env` chứa các cấu hình quan trọng cho hệ thống Chat AI:
- **GOOGLE_API_KEY**: API key cho Google Gemini (LLM)
- **SQL Connection**: Thông tin kết nối SQL Server

## 🔑 Bước 1: Lấy Google API Key

### Cách 1: Google AI Studio (Khuyến nghị)
1. Truy cập: https://aistudio.google.com/app/apikey
2. Đăng nhập bằng Google account
3. Click "Create API Key"
4. Copy API key (dạng: `AIzaSy...`)

### Cách 2: Google Maker Suite (Cũ)
1. Truy cập: https://makersuite.google.com/app/apikey
2. Đăng nhập và tạo API key

### Thêm vào .env:
```env
GOOGLE_API_KEY=AIzaSy...your_api_key_here
```

## 🗄️ Bước 2: Cấu hình SQL Server

### Option 1: Windows Authentication (Khuyến nghị - Đơn giản nhất)

**Nếu SQL Server trên cùng máy và dùng Windows Authentication:**

```env
SQL_SERVER=localhost
SQL_DATABASE=THITHI_AI
SQL_TRUSTED_CONNECTION=yes
```

**Hoặc dùng connection string:**
```env
SQL_CONNECTION_STRING=DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=THITHI_AI;Trusted_Connection=yes;TrustServerCertificate=yes;
```

### Option 2: SQL Server Authentication

**Nếu dùng username/password:**

```env
SQL_SERVER=localhost
SQL_DATABASE=THITHI_AI
SQL_TRUSTED_CONNECTION=no
SQL_USERNAME=your_username
SQL_PASSWORD=your_password
```

**Hoặc connection string:**
```env
SQL_CONNECTION_STRING=DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=THITHI_AI;UID=your_username;PWD=your_password;TrustServerCertificate=yes;
```

### Option 3: SQL Server trên máy khác

**Nếu SQL Server trên máy khác trong mạng:**

```env
SQL_SERVER=192.168.1.100  # IP hoặc hostname
SQL_DATABASE=THITHI_AI
SQL_TRUSTED_CONNECTION=yes
# Hoặc
# SQL_USERNAME=your_username
# SQL_PASSWORD=your_password
```

## ✅ Kiểm tra cấu hình

### 1. Kiểm tra file .env tồn tại

```bash
# Windows
dir .env

# Hoặc mở file
notepad .env
```

### 2. Test SQL Connection

Tạo file `test_sql_connection.py`:

```python
import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

# Lấy connection string
connection_string = os.getenv("SQL_CONNECTION_STRING")
if not connection_string:
    # Build từ individual settings
    server = os.getenv("SQL_SERVER", "localhost")
    database = os.getenv("SQL_DATABASE", "THITHI_AI")
    trusted = os.getenv("SQL_TRUSTED_CONNECTION", "yes")
    
    if trusted.lower() == "yes":
        connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;TrustServerCertificate=yes;"
    else:
        username = os.getenv("SQL_USERNAME")
        password = os.getenv("SQL_PASSWORD")
        connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes;"

try:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    cursor.execute("SELECT @@VERSION")
    version = cursor.fetchone()[0]
    print("✅ Kết nối SQL Server thành công!")
    print(f"Version: {version[:50]}...")
    conn.close()
except Exception as e:
    print(f"❌ Lỗi kết nối SQL Server: {e}")
```

Chạy:
```bash
python test_sql_connection.py
```

### 3. Test Google API Key

Tạo file `test_google_api.py`:

```python
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

if not api_key or api_key == "your_google_api_key_here":
    print("❌ GOOGLE_API_KEY chưa được cấu hình trong .env")
    print("   Vui lòng thêm GOOGLE_API_KEY=your_api_key vào file .env")
else:
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=api_key,
            temperature=0.7
        )
        response = llm.invoke("Xin chào, bạn có hoạt động không?")
        print("✅ Google API Key hợp lệ!")
        print(f"Response: {response.content[:100]}...")
    except Exception as e:
        print(f"❌ Lỗi với Google API Key: {e}")
        print("   Kiểm tra lại API key trong .env")
```

Chạy:
```bash
python test_google_api.py
```

## 🔧 Troubleshooting

### Lỗi: "GOOGLE_API_KEY not found"

**Giải pháp:**
1. Kiểm tra file `.env` có tồn tại không
2. Kiểm tra tên biến: `GOOGLE_API_KEY` (không có khoảng trắng)
3. Đảm bảo không có dấu ngoặc kép thừa: `GOOGLE_API_KEY="key"` → `GOOGLE_API_KEY=key`
4. Restart Python sau khi sửa .env

### Lỗi: "Cannot connect to SQL Server"

**Giải pháp:**
1. Kiểm tra SQL Server đang chạy:
   ```bash
   # Windows Services
   services.msc
   # Tìm "SQL Server (MSSQLSERVER)" hoặc tên instance của bạn
   ```

2. Kiểm tra SQL Server Browser đang chạy (nếu dùng named instance)

3. Kiểm tra firewall:
   ```bash
   # Cho phép SQL Server qua firewall
   # Port mặc định: 1433
   ```

4. Kiểm tra ODBC Driver:
   ```bash
   # Windows: Control Panel > Administrative Tools > ODBC Data Sources
   # Kiểm tra có "ODBC Driver 17 for SQL Server" không
   ```

5. Test connection string:
   ```python
   import pyodbc
   conn = pyodbc.connect("DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=THITHI_AI;Trusted_Connection=yes;TrustServerCertificate=yes;")
   ```

### Lỗi: "ODBC Driver 17 for SQL Server not found"

**Giải pháp:**
1. Download và cài đặt: https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
2. Hoặc dùng driver khác:
   ```env
   SQL_CONNECTION_STRING=DRIVER={SQL Server};SERVER=localhost;DATABASE=THITHI_AI;Trusted_Connection=yes;
   ```

## 📋 Checklist

Trước khi chạy services, đảm bảo:

- [ ] File `.env` tồn tại trong thư mục `THITHI_python-api`
- [ ] `GOOGLE_API_KEY` đã được điền (không phải `your_google_api_key_here`)
- [ ] SQL connection đã được cấu hình đúng
- [ ] SQL Server đang chạy
- [ ] Database `THITHI_AI` đã được tạo
- [ ] Đã test connection thành công

## 🎯 Ví dụ file .env hoàn chỉnh

```env
# Google API Key
GOOGLE_API_KEY=your_google_api_key_here

# SQL Server - Windows Authentication
SQL_SERVER=localhost
SQL_DATABASE=THITHI_AI
SQL_TRUSTED_CONNECTION=yes

# RAG Configuration
RAG_TABLE_NAME=rag_documents
DATA_DIR=./data

# Embedding
USE_SQL_EMBEDDINGS=false
PYTHON_API_URL=http://localhost:5005/vectorize
EMBEDDING_DIMENSION=768

# Chunking
CHUNK_SIZE=1000
CHUNK_OVERLAP=100

# Ports
PORT=5005
```

## 📝 Lưu ý

1. **Không commit file .env vào Git**: File `.env` chứa thông tin nhạy cảm
2. **Backup .env**: Lưu backup file .env ở nơi an toàn
3. **Restart sau khi sửa**: Sau khi sửa .env, cần restart Python services
4. **Kiểm tra encoding**: Đảm bảo file .env là UTF-8, không có BOM

## 🔗 Tài liệu liên quan

- `START_SERVICES.md` - Hướng dẫn khởi động services
- `FIX_CHAT_NOT_FOUND.md` - Sửa lỗi không tìm thấy thông tin
- `env_template.txt` - Template file .env
