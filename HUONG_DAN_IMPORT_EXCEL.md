# Hướng Dẫn Import Excel vào SQL Server với Vector Embeddings

Script này cho phép bạn import file Excel từ thư mục `C:\MyData\projects\THITHI\Data` vào SQL Server 2025 với vector embeddings cho dữ liệu ngữ nghĩa.

## Tính năng

- ✅ Tự động đọc tất cả file Excel (.xlsx, .xls) từ thư mục Data
- ✅ Tự động phát hiện cột text (ngữ nghĩa), cột số (numeric) và cột datetime
- ✅ Tạo vector embeddings cho dữ liệu ngữ nghĩa
- ✅ Lưu cả dữ liệu gốc (text, số, datetime) và vector vào SQL Server 2025
- ✅ Hỗ trợ VECTOR type của SQL Server 2025
- ✅ Cột datetime được lưu để thống kê và đếm theo thời gian

## Yêu cầu

1. **Python API đang chạy**: Script cần Python API chạy tại `http://localhost:5005` để tạo embeddings
   ```bash
   # Chạy Python API (từ thư mục THITHI_python-api)
   python app.py
   ```

2. **Cài đặt dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Cấu hình SQL Server**: Đảm bảo file `.env` có cấu hình SQL Server:
   ```env
   SQL_SERVER=localhost
   SQL_DATABASE=THITHI_AI
   SQL_TRUSTED_CONNECTION=yes
   # Hoặc
   # SQL_CONNECTION_STRING=DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=THITHI_AI;Trusted_Connection=yes;TrustServerCertificate=yes;
   ```

## Cách sử dụng

### 1. Import tất cả file Excel trong thư mục Data

```bash
# Windows Batch
import_excel.bat

# PowerShell
.\import_excel.ps1

# Hoặc trực tiếp
python excel_to_sql_vector.py
```

### 2. Import một file Excel cụ thể

```bash
python excel_to_sql_vector.py --file "C:\MyData\projects\THITHI\Data\TSTN-1P-2021.xlsx"
```

### 3. Chỉ định tên bảng

```bash
python excel_to_sql_vector.py --file "C:\MyData\projects\THITHI\Data\TSTN-1P-2021.xlsx" --table "MyTable"
```

### 4. Chỉ định sheet cụ thể

```bash
python excel_to_sql_vector.py --file "C:\MyData\projects\THITHI\Data\TSTN-1P-2021.xlsx" --sheet "Sheet1"
```

### 5. Tùy chỉnh batch size

```bash
python excel_to_sql_vector.py --batch-size 100
```

## Cấu trúc bảng được tạo

Script sẽ tự động tạo bảng với cấu trúc:

- **Cột gốc từ Excel**: 
  - Cột text (NVARCHAR): Dữ liệu ngữ nghĩa → tạo vector
  - Cột số (FLOAT): Dữ liệu số → dùng cho tính toán, thống kê
  - Cột datetime (DATETIME2): Ngày tháng năm → dùng cho thống kê, đếm theo thời gian
- **CombinedText**: Chuỗi kết hợp các cột text để vectorize
- **VectorJson**: Embedding dạng JSON (backup)
- **Embedding**: VECTOR type (SQL Server 2025) - 768 dimensions
- **SourceFile**: Tên file Excel gốc
- **RowIndex**: Chỉ số dòng trong Excel
- **CreatedAt**: Thời gian import

## Cách hoạt động

1. **Phát hiện cột**: Script tự động phân loại:
   - **Cột text (ngữ nghĩa)**: Cột có kiểu object/string và chứa text dài > 5 ký tự → tạo vector embeddings
   - **Cột số (numeric)**: Cột có kiểu số (int, float) → lưu để tính toán, thống kê
   - **Cột datetime**: Cột có kiểu datetime64 hoặc string có thể parse thành datetime → lưu để thống kê, đếm theo thời gian

2. **Tạo vector**: 
   - Kết hợp tất cả cột text thành một chuỗi
   - Gửi đến Python API để tạo embeddings (768 dimensions)
   - Lưu vào cột `Embedding` (VECTOR type) và `VectorJson` (backup)

3. **Lưu vào SQL Server**:
   - Tạo bảng tự động nếu chưa tồn tại
   - Insert dữ liệu theo batch để tối ưu hiệu suất

## Ví dụ kết quả

```json
{
  "status": "success",
  "message": "Đã import thành công 150 dòng",
  "file": "C:\\MyData\\projects\\THITHI\\Data\\TSTN-1P-2021.xlsx",
  "table_name": "TSTN_1P_2021",
  "rows_imported": 150,
  "total_rows": 150,
  "text_columns": ["TenSanPham", "MoTa", "DanhMuc"],
  "numeric_columns": ["Gia", "SoLuong", "TonKho"],
  "has_embeddings": true
}
```

## Lưu ý

1. **Python API phải chạy**: Script cần Python API (`app.py`) đang chạy để tạo embeddings
2. **SQL Server 2025**: Cần SQL Server 2025+ để hỗ trợ VECTOR type. Nếu dùng SQL Server cũ hơn, chỉ có `VectorJson` được lưu.
3. **Batch size**: Mặc định 50 dòng/batch. Có thể tăng nếu có nhiều RAM.
4. **Tên bảng**: Tên bảng được tạo từ tên file (loại bỏ khoảng trắng và ký tự đặc biệt)

## Troubleshooting

### Lỗi: "Không thể kết nối đến Python API"
- Đảm bảo Python API đang chạy: `python app.py`
- Kiểm tra URL trong `.env`: `PYTHON_API_URL=http://localhost:5005/vectorize`

### Lỗi: "Không thể kết nối đến SQL Server"
- Kiểm tra cấu hình trong `.env`
- Đảm bảo SQL Server đang chạy
- Kiểm tra quyền truy cập database

### Lỗi: "Table không tồn tại"
- Script sẽ tự động tạo bảng, nhưng cần quyền CREATE TABLE

### Không có vector embeddings
- Kiểm tra có cột text trong Excel không
- Kiểm tra Python API có đang chạy không
- Xem logs để biết lỗi cụ thể

## Query dữ liệu với vector search

Sau khi import, bạn có thể tìm kiếm semantic:

```sql
-- Tìm kiếm semantic
DECLARE @queryVector NVARCHAR(MAX) = '[0.1,0.2,0.3,...]';  -- Vector từ query

SELECT TOP 10
    ID,
    TenSanPham,
    MoTa,
    Gia,
    (1.0 - VECTOR_DISTANCE(Embedding, CAST(@queryVector AS VECTOR(768)), COSINE)) AS Similarity
FROM dbo.[TSTN_1P_2021]
WHERE Embedding IS NOT NULL
ORDER BY VECTOR_DISTANCE(Embedding, CAST(@queryVector AS VECTOR(768)), COSINE) ASC;
```

## Thống kê và tính toán

Dữ liệu số và datetime được lưu để tính toán và thống kê:

```sql
-- Thống kê theo danh mục
SELECT 
    DanhMuc,
    COUNT(*) AS SoLuong,
    SUM(Gia) AS TongGia,
    AVG(Gia) AS GiaTrungBinh
FROM dbo.[TSTN_1P_2021]
GROUP BY DanhMuc;

-- Thống kê theo thời gian (ngày tháng năm)
SELECT 
    CAST(NgayTao AS DATE) AS Ngay,
    COUNT(*) AS SoLuong,
    SUM(Gia) AS TongGia
FROM dbo.[TSTN_1P_2021]
WHERE NgayTao IS NOT NULL
GROUP BY CAST(NgayTao AS DATE)
ORDER BY Ngay DESC;

-- Thống kê theo tháng
SELECT 
    YEAR(NgayTao) AS Nam,
    MONTH(NgayTao) AS Thang,
    COUNT(*) AS SoLuong,
    SUM(Gia) AS TongGia
FROM dbo.[TSTN_1P_2021]
WHERE NgayTao IS NOT NULL
GROUP BY YEAR(NgayTao), MONTH(NgayTao)
ORDER BY Nam DESC, Thang DESC;
```
