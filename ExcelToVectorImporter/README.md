# Excel to Vector Importer

A C# Console Application to import data from Excel files into SQL Server 2025 with native VECTOR support for RAG (Retrieval-Augmented Generation) Chatbot systems.

## Features

- ✅ Reads Excel files (`.xlsx`) using EPPlus
- ✅ Generates embeddings using OpenAI `text-embedding-3-small` (1536 dimensions)
- ✅ Inserts data into SQL Server 2025 with native `VECTOR(1536)` data type
- ✅ Batch processing to optimize API calls and database operations
- ✅ Async/await for optimal performance
- ✅ Comprehensive error handling and logging

## Prerequisites

1. **.NET 8.0 SDK** or later
2. **SQL Server 2025** with compatibility level 180
3. **OpenAI API Key** (for generating embeddings)
4. **Excel file** (`Products.xlsx`) with the following columns:
   - `ProductId` (required)
   - `ProductName` (required)
   - `Category` (optional)
   - `Description` (optional)
   - `Price` (optional)
   - `StockQuantity` (optional)
   - `LastUpdated` (optional)

## Setup

### 1. Create Database Table

First, run the SQL script to create the `Products_Hybrid` table:

```sql
-- Run CreateProductsHybridTable.sql in SQL Server Management Studio
-- Or use sqlcmd:
sqlcmd -S localhost -U sa -P YourPassword -d THITHI_AI -i CreateProductsHybridTable.sql
```

### 2. Configure Application

Edit `appsettings.json`:

```json
{
  "ConnectionStrings": {
    "SqlServer": "Server=localhost;Database=THITHI_AI;User Id=sa;Password=YourPassword;TrustServerCertificate=True;"
  },
  "OpenAI": {
    "ApiKey": "sk-your-openai-api-key-here",
    "Model": "text-embedding-3-small",
    "Dimensions": 1536
  },
  "Processing": {
    "BatchSize": 50,
    "MaxRetries": 3,
    "RetryDelayMs": 1000
  }
}
```

**Important:** 
- Replace `YourPassword` with your SQL Server password
- Replace `sk-your-openai-api-key-here` with your actual OpenAI API key
- Adjust `BatchSize` based on your API rate limits (default: 50)

### 3. Build the Application

```bash
cd ExcelToVectorImporter
dotnet restore
dotnet build
```

## Usage

### Basic Usage

Place your `Products.xlsx` file in the same directory as the executable, then run:

```bash
dotnet run
```

Or specify the Excel file path:

```bash
dotnet run Products.xlsx
```

### After Building

```bash
dotnet run -- Products.xlsx
# Or
.\bin\Debug\net8.0\ExcelToVectorImporter.exe Products.xlsx
```

## How It Works

1. **Read Excel File**: Reads all rows from the Excel file and parses them into `Product` objects
2. **Build Text Context**: For each product, constructs a text block:
   ```
   Product: {ProductName}. Category: {Category}. Description: {Description}. Price: {Price}.
   ```
3. **Generate Embeddings**: Calls OpenAI API to generate 1536-dimensional embeddings for each text block
4. **Batch Processing**: Processes products in batches (default: 50) to optimize API calls
5. **Insert to Database**: Inserts products with their vector embeddings into SQL Server 2025

## Database Schema

The `Products_Hybrid` table includes:

- **Structured Columns**: `ProductId`, `ProductName`, `Category`, `Description`, `Price`, `StockQuantity`, `LastUpdated`
- **Vector Column**: `SearchVector VECTOR(1536)` for semantic search
- **Full Text**: `FullTextContext NVARCHAR(MAX)` storing the combined text representation
- **Indexes**: 
  - Regular indexes on `ProductId`, `Category`, `Price`, `LastUpdated`
  - HNSW vector index on `SearchVector` for fast similarity search

## Vector Search Example

After importing, you can search using vector similarity:

```sql
-- Example: Search for products similar to a query
DECLARE @queryText NVARCHAR(MAX) = 'Product: Laptop. Category: Electronics. Description: High-performance laptop. Price: $999.00.';
-- First, get the embedding for this query (using your application or API)
DECLARE @queryVector NVARCHAR(MAX) = '[0.1,0.2,0.3,...]'; -- Your query embedding

EXEC sp_SearchProductsByVector
    @queryVector = @queryVector,
    @similarityThreshold = 0.7,
    @topN = 10,
    @categoryFilter = NULL,
    @minPrice = NULL,
    @maxPrice = NULL;
```

## Configuration Options

### Batch Size

Adjust `BatchSize` in `appsettings.json` based on:
- **API Rate Limits**: OpenAI has rate limits (requests per minute)
- **Memory**: Larger batches use more memory
- **Network**: Larger batches take longer per request

Recommended values:
- **Small datasets (< 100 products)**: 50-100
- **Medium datasets (100-1000 products)**: 50
- **Large datasets (> 1000 products)**: 25-50

### Retry Settings

```json
"Processing": {
  "BatchSize": 50,
  "MaxRetries": 3,
  "RetryDelayMs": 1000
}
```

## Troubleshooting

### Error: "Table Products_Hybrid does not exist"

**Solution**: Run the SQL script `CreateProductsHybridTable.sql` first.

### Error: "OpenAI:ApiKey is not configured"

**Solution**: Add your OpenAI API key to `appsettings.json` under `OpenAI:ApiKey`.

### Error: "Database connection failed"

**Solution**: 
- Check your connection string in `appsettings.json`
- Ensure SQL Server is running
- Verify database name and credentials
- Check firewall settings

### Error: "VECTOR is not a recognized built-in function name"

**Solution**: 
- Ensure SQL Server 2025 is installed
- Set database compatibility level to 180:
  ```sql
  ALTER DATABASE [THITHI_AI] SET COMPATIBILITY_LEVEL = 180;
  ```

### Rate Limit Errors from OpenAI

**Solution**: 
- Reduce `BatchSize` in `appsettings.json`
- Increase delay between batches (modify `Program.cs`)
- Use OpenAI API with higher rate limits

## Performance Tips

1. **Use Batch Processing**: The application processes in batches by default
2. **Optimize Batch Size**: Find the sweet spot between API rate limits and processing speed
3. **Use Vector Index**: The HNSW index is created automatically for fast similarity search
4. **Monitor API Usage**: Keep track of your OpenAI API usage to avoid unexpected costs

## Cost Estimation

For OpenAI `text-embedding-3-small`:
- **Price**: $0.02 per 1M tokens
- **Average**: ~50-100 tokens per product (depending on description length)
- **Example**: 10,000 products ≈ 500K-1M tokens ≈ $0.01-$0.02

## License

EPPlus requires a license for commercial use. The project is configured for non-commercial use by default. For commercial projects, update `ExcelService.cs`:

```csharp
ExcelPackage.LicenseContext = LicenseContext.Commercial;
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review SQL Server 2025 VECTOR documentation
3. Check OpenAI API documentation for rate limits and pricing
