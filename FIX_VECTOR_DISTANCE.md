# Hướng Dẫn: Sửa Lỗi VECTOR_DISTANCE

## 🔍 Vấn đề

Lỗi: `Argument data type vector is invalid for argument 1 of vector_distance function`

Lỗi này xảy ra khi SQL Server không nhận diện được format vector string trong VECTOR_DISTANCE function.

## ✅ Giải pháp đã áp dụng

### 1. Thử nhiều cách format vector

Code đã được cập nhật để thử 3 cách format khác nhau:

**Cách 1: DECLARE variable riêng (khuyến nghị)**
```sql
DECLARE @queryVector NVARCHAR(MAX) = '[vector_string]';
DECLARE @queryVectorTyped VECTOR(768) = CAST(@queryVector AS VECTOR(768));
SELECT ... VECTOR_DISTANCE(Embedding, @queryVectorTyped, 'COSINE') ...
```

**Cách 2: CAST trực tiếp trong query**
```sql
DECLARE @queryVectorStr NVARCHAR(MAX) = '[vector_string]';
SELECT ... VECTOR_DISTANCE(Embedding, CAST(@queryVectorStr AS VECTOR(768)), 'COSINE') ...
```

**Cách 3: Format đơn giản (decimal, không scientific)**
```sql
-- Dùng format: [0.123456,0.234567,...] thay vì scientific notation
```

### 2. Kiểm tra SQL Server version

Code sẽ tự động kiểm tra:
- SQL Server version
- Embedding column type
- Hỗ trợ VECTOR type

### 3. Fallback về VectorJson

Nếu tất cả cách đều fail, sẽ fallback về dùng VectorJson column (nếu có).

## 🔧 Debug

Chạy script debug để xem cách nào hoạt động:

```bash
python debug_api.py
```

Script sẽ:
- ✅ Kiểm tra SQL Server version
- ✅ Kiểm tra Embedding column type
- ✅ Thử 3 cách format vector khác nhau
- ✅ Báo cáo cách nào hoạt động

## 📋 Checklist

Nếu vẫn gặp lỗi:

1. **Kiểm tra SQL Server version:**
   ```sql
   SELECT @@VERSION
   ```
   Cần SQL Server 2025+ (version 16+) để hỗ trợ VECTOR type.

2. **Kiểm tra Embedding column type:**
   ```sql
   SELECT TYPE_NAME(system_type_id) 
   FROM sys.columns 
   WHERE object_id = OBJECT_ID('dbo.[TSMay]') AND name = 'Embedding'
   ```
   Phải là `VECTOR` hoặc `vector`.

3. **Kiểm tra data có đúng format không:**
   ```sql
   SELECT TOP 1 Embedding FROM dbo.[TSMay] WHERE Embedding IS NOT NULL
   ```

4. **Test với vector đơn giản:**
   ```sql
   DECLARE @v VECTOR(768) = CAST('[0.1,0.2,0.3]' AS VECTOR(768));
   SELECT @v;
   ```

## 🎯 Workaround: Dùng VectorJson

Nếu VECTOR type không hoạt động, có thể dùng VectorJson:

1. **Import lại dữ liệu với VectorJson:**
   ```bash
   python excel_to_sql_vector.py --file "path/to/file.xlsx" --table "TSMay"
   ```

2. **Code sẽ tự động fallback về VectorJson** nếu VECTOR type fail.

## 💡 Tips

1. **Format vector string:**
   - Dùng format đơn giản: `[0.123,0.456,...]`
   - Tránh scientific notation nếu có thể
   - Không có khoảng trắng

2. **SQL Server version:**
   - SQL Server 2025 (version 16+) mới hỗ trợ VECTOR type
   - Nếu dùng version cũ, dùng VectorJson

3. **Debug:**
   - Chạy `python debug_api.py` để xem lỗi cụ thể
   - Check logs trong `app.py` để xem cách nào được dùng

## 🔗 Tài liệu liên quan

- `debug_api.py` - Script debug chi tiết
- `FIX_500_ERROR.md` - Sửa lỗi 500
- `app.py` - Code đã được cập nhật với fallback
