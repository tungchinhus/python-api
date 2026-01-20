# Hướng Dẫn Fix Lỗi Import Excel

## Lỗi: `'INDEX_TYPE' is not a recognized CREATE VECTOR INDEX option`

Lỗi này xảy ra khi backend cố gắng tạo VECTOR INDEX với syntax không được SQL Server 2025 hỗ trợ.

## ✅ Đã Sửa

Code đã được sửa trong file `VectorImportService.cs`:
- Đã bỏ phần tự động tạo VECTOR INDEX với `INDEX_TYPE = HNSW`
- Import sẽ chỉ tạo bảng và cột VECTOR, không tạo index tự động

## 🔧 Các Bước Để Fix

### Bước 1: Dừng Backend (nếu đang chạy)

1. Mở **Task Manager** (Ctrl + Shift + Esc)
2. Tìm process `dotnet` hoặc `THIHI_AI.Backend`
3. End process đó

**Hoặc dùng PowerShell:**
```powershell
Get-Process -Name "dotnet" | Where-Object { $_.Path -like "*THIHI_AI.Backend*" } | Stop-Process -Force
```

### Bước 2: Rebuild Backend Project

Mở PowerShell hoặc Command Prompt và chạy:

```powershell
# Chuyển đến thư mục backend
cd C:\MyData\projects\THITHI\THIHI_AI\backend\THIHI_AI.Backend

# Clean project
dotnet clean

# Build lại project
dotnet build --configuration Release
```

**Hoặc dùng script tự động:**
```powershell
cd C:\MyData\projects\THITHI\THIHI_AI\backend
.\rebuild-and-restart.ps1
```

### Bước 3: Khởi động lại Backend

```powershell
cd C:\MyData\projects\THITHI\THIHI_AI\backend\THIHI_AI.Backend
dotnet run --configuration Release
```

Backend sẽ chạy tại: `http://localhost:5000`

### Bước 4: Thử Import Lại

1. Mở ứng dụng web (Angular frontend)
2. Chọn file Excel
3. Chọn "SQL Server (.NET Backend)"
4. Click Import

## 🔍 Kiểm Tra

Sau khi import thành công, bạn có thể kiểm tra trong SQL Server:

```sql
-- Kiểm tra bảng đã được tạo
SELECT * FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_NAME LIKE 'TSMay%';

-- Kiểm tra dữ liệu đã import
SELECT TOP 10 * FROM dbo.[TSMay];

-- Kiểm tra cột VECTOR
SELECT 
    COLUMN_NAME,
    DATA_TYPE,
    CHARACTER_MAXIMUM_LENGTH
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'TSMay' AND COLUMN_NAME = 'Embedding';
```

## 📝 Tạo VECTOR INDEX Thủ Công (Tùy Chọn)

Nếu muốn tạo VECTOR INDEX để tăng tốc tìm kiếm, chạy SQL script này **SAU KHI** import xong:

```sql
-- Thay 'TSMay' bằng tên bảng của bạn
DECLARE @tableName NVARCHAR(255) = 'TSMay';
DECLARE @indexName NVARCHAR(255) = 'IX_' + @tableName + '_Embedding';
DECLARE @sql NVARCHAR(MAX);

-- Kiểm tra xem index đã tồn tại chưa
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes 
    WHERE name = @indexName 
    AND object_id = OBJECT_ID('dbo.[' + @tableName + ']')
)
BEGIN
    SET @sql = N'
    CREATE VECTOR INDEX ' + @indexName + ' 
    ON dbo.[' + @tableName + '](Embedding)
    WITH (DISTANCE_FUNCTION = COSINE);
    ';
    
    EXEC sp_executesql @sql;
    PRINT 'Vector index đã được tạo: ' + @indexName;
END
ELSE
BEGIN
    PRINT 'Index đã tồn tại: ' + @indexName;
END
```

**Lưu ý:** Syntax VECTOR INDEX có thể khác nhau tùy theo version SQL Server 2025. Nếu script trên không chạy được, thử:

```sql
-- Syntax đơn giản hơn
CREATE VECTOR INDEX IX_TSMay_Embedding 
ON dbo.[TSMay](Embedding);
```

## ⚠️ Troubleshooting

### Lỗi vẫn còn sau khi rebuild

1. **Kiểm tra code đã được save chưa:**
   - Mở file `VectorImportService.cs`
   - Tìm dòng 278-280
   - Đảm bảo không còn `CREATE VECTOR INDEX` với `INDEX_TYPE = HNSW`

2. **Clear cache và rebuild:**
   ```powershell
   cd C:\MyData\projects\THITHI\THIHI_AI\backend\THIHI_AI.Backend
   dotnet clean
   Remove-Item -Recurse -Force bin, obj -ErrorAction SilentlyContinue
   dotnet build --configuration Release
   ```

3. **Kiểm tra backend đang chạy code mới:**
   - Xem log khi start backend
   - Đảm bảo không có lỗi compile

### Backend không start được

- Kiểm tra port 5000 có bị chiếm không:
  ```powershell
  netstat -ano | findstr :5000
  ```
- Kiểm tra connection string trong `appsettings.json`
- Kiểm tra SQL Server đang chạy

## 📞 Liên Hệ

Nếu vẫn gặp lỗi, kiểm tra:
1. SQL Server version (phải >= 2025)
2. Database compatibility level (phải = 180)
3. Backend logs để xem lỗi chi tiết
