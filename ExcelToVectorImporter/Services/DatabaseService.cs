using System.Data;
using System.Text;
using ExcelToVectorImporter.Models;
using Microsoft.Data.SqlClient;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;

namespace ExcelToVectorImporter.Services;

public class DatabaseService
{
    private readonly ILogger<DatabaseService> _logger;
    private readonly string _connectionString;

    public DatabaseService(IConfiguration configuration, ILogger<DatabaseService> logger)
    {
        _logger = logger;
        _connectionString = configuration.GetConnectionString("SqlServer") 
            ?? throw new InvalidOperationException("SqlServer connection string is not configured");
    }

    /// <summary>
    /// Converts a float array to SQL Server VECTOR format string
    /// Format: [0.1,0.2,0.3,...] (no spaces)
    /// </summary>
    private string ConvertToVectorString(float[] embedding)
    {
        if (embedding == null || embedding.Length == 0)
            throw new ArgumentException("Embedding cannot be null or empty", nameof(embedding));

        var sb = new StringBuilder();
        sb.Append('[');
        
        for (int i = 0; i < embedding.Length; i++)
        {
            if (i > 0)
                sb.Append(',');
            
            // Format as decimal without scientific notation
            sb.Append(embedding[i].ToString("F6", System.Globalization.CultureInfo.InvariantCulture));
        }
        
        sb.Append(']');
        return sb.ToString();
    }

    /// <summary>
    /// Inserts a batch of products into SQL Server
    /// </summary>
    public async Task<int> InsertProductsBatchAsync(List<Product> products, CancellationToken cancellationToken = default)
    {
        if (products == null || products.Count == 0)
            return 0;

        var insertedCount = 0;

        try
        {
            using var connection = new SqlConnection(_connectionString);
            await connection.OpenAsync(cancellationToken);

            // Use a transaction for batch insert
            using var transaction = connection.BeginTransaction();
            
            try
            {
                foreach (var product in products)
                {
                    if (product.Embedding == null || product.Embedding.Length == 0)
                    {
                        _logger.LogWarning("Skipping product {ProductId} - no embedding available", product.ProductId);
                        continue;
                    }

                    var vectorString = ConvertToVectorString(product.Embedding);

                    var sql = @"
                        INSERT INTO dbo.Products_Hybrid 
                        (ProductId, ProductName, Category, Description, Price, StockQuantity, LastUpdated, SearchVector, FullTextContext, UpdatedAt)
                        VALUES 
                        (@ProductId, @ProductName, @Category, @Description, @Price, @StockQuantity, @LastUpdated, 
                         CAST(@SearchVector AS VECTOR(1536)), @FullTextContext, GETDATE())";

                    using var command = new SqlCommand(sql, connection, transaction);
                    
                    command.Parameters.AddWithValue("@ProductId", product.ProductId);
                    command.Parameters.AddWithValue("@ProductName", product.ProductName);
                    command.Parameters.AddWithValue("@Category", (object?)product.Category ?? DBNull.Value);
                    command.Parameters.AddWithValue("@Description", (object?)product.Description ?? DBNull.Value);
                    command.Parameters.AddWithValue("@Price", (object?)product.Price ?? DBNull.Value);
                    command.Parameters.AddWithValue("@StockQuantity", (object?)product.StockQuantity ?? DBNull.Value);
                    command.Parameters.AddWithValue("@LastUpdated", (object?)product.LastUpdated ?? DBNull.Value);
                    command.Parameters.AddWithValue("@SearchVector", vectorString);
                    command.Parameters.AddWithValue("@FullTextContext", product.FullTextContext);

                    await command.ExecuteNonQueryAsync(cancellationToken);
                    insertedCount++;
                }

                transaction.Commit();
                _logger.LogInformation("Successfully inserted {Count} products into database", insertedCount);
            }
            catch
            {
                transaction.Rollback();
                throw;
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error inserting products batch into database");
            throw;
        }

        return insertedCount;
    }

    /// <summary>
    /// Tests the database connection
    /// </summary>
    public async Task<bool> TestConnectionAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            using var connection = new SqlConnection(_connectionString);
            await connection.OpenAsync(cancellationToken);
            
            // Test if table exists
            var sql = @"
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'Products_Hybrid'";
            
            using var command = new SqlCommand(sql, connection);
            var tableExists = (int)await command.ExecuteScalarAsync(cancellationToken) > 0;
            
            if (!tableExists)
            {
                _logger.LogWarning("Table Products_Hybrid does not exist. Please run the SQL script first.");
                return false;
            }

            _logger.LogInformation("Database connection test successful");
            return true;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Database connection test failed");
            return false;
        }
    }

    /// <summary>
    /// Gets the count of products in the database
    /// </summary>
    public async Task<int> GetProductCountAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            using var connection = new SqlConnection(_connectionString);
            await connection.OpenAsync(cancellationToken);

            var sql = "SELECT COUNT(*) FROM dbo.Products_Hybrid";
            using var command = new SqlCommand(sql, connection);
            
            var count = (int)await command.ExecuteScalarAsync(cancellationToken);
            return count;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting product count");
            throw;
        }
    }
}
