-- =============================================
-- SQL Script: Create Products_Hybrid Table
-- Database: SQL Server 2025
-- Purpose: RAG Chatbot System with Vector Search
-- =============================================

USE [THITHI_AI]; -- Change to your database name
GO

-- Drop table if exists (for testing/recreation)
IF OBJECT_ID('dbo.Products_Hybrid', 'U') IS NOT NULL
    DROP TABLE dbo.Products_Hybrid;
GO

-- Create Products_Hybrid table
CREATE TABLE dbo.Products_Hybrid
(
    Id INT IDENTITY(1,1) PRIMARY KEY,
    ProductId NVARCHAR(50) NOT NULL,
    ProductName NVARCHAR(255) NOT NULL,
    Category NVARCHAR(100) NULL,
    Description NVARCHAR(MAX) NULL,
    Price DECIMAL(18,2) NULL,
    StockQuantity INT NULL,
    LastUpdated DATETIME2 NULL,
    
    -- Vector embedding column for semantic search (1536 dimensions for OpenAI text-embedding-3-small)
    SearchVector VECTOR(1536) NULL,
    
    -- Full text context for embedding generation
    FullTextContext NVARCHAR(MAX) NULL,
    
    -- Metadata
    CreatedAt DATETIME2 DEFAULT GETDATE(),
    UpdatedAt DATETIME2 DEFAULT GETDATE(),
    
    -- Indexes for performance
    INDEX IX_Products_Hybrid_ProductId NONCLUSTERED (ProductId),
    INDEX IX_Products_Hybrid_Category NONCLUSTERED (Category),
    INDEX IX_Products_Hybrid_Price NONCLUSTERED (Price),
    INDEX IX_Products_Hybrid_LastUpdated NONCLUSTERED (LastUpdated)
);
GO

-- Create HNSW Vector Index for fast similarity search (SQL Server 2025+)
-- This index significantly improves vector search performance
IF EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Products_Hybrid_SearchVector' AND object_id = OBJECT_ID('dbo.Products_Hybrid'))
    DROP INDEX IX_Products_Hybrid_SearchVector ON dbo.Products_Hybrid;
GO

CREATE VECTOR INDEX IX_Products_Hybrid_SearchVector
ON dbo.Products_Hybrid (SearchVector)
WITH (
    INDEX_TYPE = HNSW,
    DISTANCE_FUNCTION = COSINE,
    M = 16,
    EF_CONSTRUCTION = 64
);
GO

-- Create stored procedure for vector similarity search
IF OBJECT_ID('dbo.sp_SearchProductsByVector', 'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_SearchProductsByVector;
GO

CREATE PROCEDURE dbo.sp_SearchProductsByVector
    @queryVector NVARCHAR(MAX), -- Vector as JSON string: [0.1,0.2,0.3,...]
    @similarityThreshold FLOAT = 0.7, -- Cosine similarity threshold (0-1, higher = more similar)
    @topN INT = 10,
    @categoryFilter NVARCHAR(100) = NULL,
    @minPrice DECIMAL(18,2) = NULL,
    @maxPrice DECIMAL(18,2) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @vector VECTOR(1536) = CAST(@queryVector AS VECTOR(1536));
    
    SELECT TOP (@topN)
        p.Id,
        p.ProductId,
        p.ProductName,
        p.Category,
        p.Description,
        p.Price,
        p.StockQuantity,
        p.LastUpdated,
        p.FullTextContext,
        -- VECTOR_DISTANCE returns distance (lower = more similar)
        -- For cosine similarity: 1 - distance gives similarity score
        (1.0 - VECTOR_DISTANCE(@vector, p.SearchVector, COSINE)) AS SimilarityScore,
        VECTOR_DISTANCE(@vector, p.SearchVector, COSINE) AS Distance
    FROM dbo.Products_Hybrid p
    WHERE p.SearchVector IS NOT NULL
        AND (@categoryFilter IS NULL OR p.Category = @categoryFilter)
        AND (@minPrice IS NULL OR p.Price >= @minPrice)
        AND (@maxPrice IS NULL OR p.Price <= @maxPrice)
        AND VECTOR_DISTANCE(@vector, p.SearchVector, COSINE) <= (1.0 - @similarityThreshold)
    ORDER BY VECTOR_DISTANCE(@vector, p.SearchVector, COSINE) ASC;
END;
GO

-- Create stored procedure for statistical queries
IF OBJECT_ID('dbo.sp_GetProductStatistics', 'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_GetProductStatistics;
GO

CREATE PROCEDURE dbo.sp_GetProductStatistics
    @categoryFilter NVARCHAR(100) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT 
        COUNT(*) AS TotalProducts,
        COUNT(DISTINCT Category) AS TotalCategories,
        SUM(Price) AS TotalValue,
        AVG(Price) AS AveragePrice,
        MIN(Price) AS MinPrice,
        MAX(Price) AS MaxPrice,
        SUM(StockQuantity) AS TotalStock,
        AVG(CAST(StockQuantity AS FLOAT)) AS AverageStock
    FROM dbo.Products_Hybrid
    WHERE (@categoryFilter IS NULL OR Category = @categoryFilter);
END;
GO

-- Verify table creation
SELECT 
    t.name AS TableName,
    c.name AS ColumnName,
    TYPE_NAME(c.system_type_id) AS DataType,
    c.max_length AS MaxLength,
    c.is_nullable AS IsNullable
FROM sys.tables t
JOIN sys.columns c ON t.object_id = c.object_id
WHERE t.name = 'Products_Hybrid'
ORDER BY c.column_id;
GO

PRINT 'Products_Hybrid table created successfully!';
PRINT 'Vector index created successfully!';
PRINT 'Stored procedures created successfully!';
GO
