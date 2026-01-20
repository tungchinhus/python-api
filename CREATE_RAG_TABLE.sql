-- =============================================
-- Script tạo bảng RAG Documents cho SQL Server 2025
-- =============================================
-- Bảng này lưu trữ PDF chunks với VECTOR embeddings
-- Sử dụng VECTOR type của SQL Server 2025 để tìm kiếm semantic

-- Kiểm tra SQL Server version
SELECT 
    @@VERSION AS SqlServerVersion,
    SERVERPROPERTY('ProductVersion') AS ProductVersion;

-- Phải là SQL Server 2025 (version >= 16.0) để hỗ trợ VECTOR type

-- =============================================
-- Tạo bảng rag_documents
-- =============================================

IF OBJECT_ID('dbo.[rag_documents]', 'U') IS NOT NULL
BEGIN
    PRINT 'Bảng rag_documents đã tồn tại. Đang kiểm tra và thêm các cột cần thiết...';
    
    -- Đảm bảo các cột cần thiết tồn tại
    IF COL_LENGTH('dbo.[rag_documents]', 'Embedding') IS NULL
    BEGIN
        ALTER TABLE dbo.[rag_documents] ADD Embedding VECTOR(384) NULL;
        PRINT 'Đã thêm cột Embedding';
    END
    
    IF COL_LENGTH('dbo.[rag_documents]', 'FileName') IS NULL
    BEGIN
        ALTER TABLE dbo.[rag_documents] ADD FileName NVARCHAR(500) NULL;
        PRINT 'Đã thêm cột FileName';
    END
    
    IF COL_LENGTH('dbo.[rag_documents]', 'PageNumber') IS NULL
    BEGIN
        ALTER TABLE dbo.[rag_documents] ADD PageNumber INT NULL;
        PRINT 'Đã thêm cột PageNumber';
    END
    
    IF COL_LENGTH('dbo.[rag_documents]', 'ChunkIndex') IS NULL
    BEGIN
        ALTER TABLE dbo.[rag_documents] ADD ChunkIndex INT NULL;
        PRINT 'Đã thêm cột ChunkIndex';
    END
    
    IF COL_LENGTH('dbo.[rag_documents]', 'CreatedAt') IS NULL
    BEGIN
        ALTER TABLE dbo.[rag_documents] ADD CreatedAt DATETIME2 DEFAULT GETDATE();
        PRINT 'Đã thêm cột CreatedAt';
    END
END
ELSE
BEGIN
    -- Tạo bảng mới
    IF CAST(SERVERPROPERTY('ProductVersion') AS VARCHAR(50)) >= '16.0'
    BEGIN
        -- SQL Server 2025+ với VECTOR support
        CREATE TABLE dbo.[rag_documents] (
            ID INT IDENTITY(1,1) PRIMARY KEY,
            Content NVARCHAR(MAX) NOT NULL,
            VectorJson NVARCHAR(MAX) NULL,              -- Backup embedding (JSON format)
            Embedding VECTOR(384) NULL,                -- Native VECTOR type (SQL Server 2025)
            FileName NVARCHAR(500) NULL,               -- Tên file PDF gốc
            PageNumber INT NULL,                       -- Số trang trong PDF
            ChunkIndex INT NULL,                       -- Chỉ số chunk trong trang
            CreatedAt DATETIME2 DEFAULT GETDATE()      -- Thời gian tạo
        );
        
        PRINT 'Đã tạo bảng rag_documents với VECTOR support (SQL Server 2025)';
    END
    ELSE
    BEGIN
        -- SQL Server cũ hơn - chỉ dùng VectorJson
        CREATE TABLE dbo.[rag_documents] (
            ID INT IDENTITY(1,1) PRIMARY KEY,
            Content NVARCHAR(MAX) NOT NULL,
            VectorJson NVARCHAR(MAX) NULL,              -- Embedding dạng JSON
            FileName NVARCHAR(500) NULL,
            PageNumber INT NULL,
            ChunkIndex INT NULL,
            CreatedAt DATETIME2 DEFAULT GETDATE()
        );
        
        PRINT 'Đã tạo bảng rag_documents (SQL Server < 2025, không có VECTOR type)';
    END
END
GO

-- =============================================
-- Tạo index để tăng tốc độ tìm kiếm
-- =============================================

-- Index trên FileName để filter theo file
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_rag_documents_FileName' AND object_id = OBJECT_ID('dbo.[rag_documents]'))
BEGIN
    CREATE INDEX IX_rag_documents_FileName ON dbo.[rag_documents] (FileName);
    PRINT 'Đã tạo index IX_rag_documents_FileName';
END
GO

-- Index trên CreatedAt để sort
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_rag_documents_CreatedAt' AND object_id = OBJECT_ID('dbo.[rag_documents]'))
BEGIN
    CREATE INDEX IX_rag_documents_CreatedAt ON dbo.[rag_documents] (CreatedAt);
    PRINT 'Đã tạo index IX_rag_documents_CreatedAt';
END
GO

-- Vector index (SQL Server 2025+) - Uncomment nếu muốn tăng tốc độ vector search
-- Lưu ý: Vector index có thể tốn nhiều tài nguyên và thời gian để build
/*
IF CAST(SERVERPROPERTY('ProductVersion') AS VARCHAR(50)) >= '16.0'
BEGIN
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_rag_documents_Embedding' AND object_id = OBJECT_ID('dbo.[rag_documents]'))
    BEGIN
        CREATE VECTOR INDEX IX_rag_documents_Embedding 
        ON dbo.[rag_documents] (Embedding) 
        WITH (INDEX_TYPE = HNSW, DISTANCE_FUNCTION = COSINE);
        PRINT 'Đã tạo vector index IX_rag_documents_Embedding';
    END
END
GO
*/

-- =============================================
-- Kiểm tra bảng đã tạo
-- =============================================

SELECT 
    c.name AS ColumnName,
    t.name AS DataType,
    c.max_length AS MaxLength,
    c.is_nullable AS IsNullable
FROM sys.columns c
INNER JOIN sys.types t ON c.user_type_id = t.user_type_id
WHERE c.object_id = OBJECT_ID('dbo.[rag_documents]')
ORDER BY c.column_id;
GO

-- =============================================
-- Test query với VECTOR_DISTANCE (nếu có data)
-- =============================================

-- Ví dụ query để test vector search
/*
DECLARE @queryVector NVARCHAR(MAX) = '[0.1,0.2,0.3,...]';  -- Thay bằng vector thực tế

SELECT TOP (5)
    ID,
    Content,
    FileName,
    PageNumber,
    (1.0 - VECTOR_DISTANCE(Embedding, CAST(@queryVector AS VECTOR(384)), COSINE)) AS Similarity
FROM dbo.[rag_documents]
WHERE Embedding IS NOT NULL
ORDER BY VECTOR_DISTANCE(Embedding, CAST(@queryVector AS VECTOR(384)), COSINE) ASC;
*/

PRINT '========================================';
PRINT 'Setup hoàn tất!';
PRINT 'Bảng: rag_documents';
PRINT '========================================';
GO
