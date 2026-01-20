using ExcelToVectorImporter.Models;
using ExcelToVectorImporter.Services;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace ExcelToVectorImporter;

class Program
{
    static async Task Main(string[] args)
    {
        // Build configuration
        var configuration = new ConfigurationBuilder()
            .SetBasePath(Directory.GetCurrentDirectory())
            .AddJsonFile("appsettings.json", optional: false, reloadOnChange: true)
            .AddEnvironmentVariables()
            .Build();

        // Setup logging
        using var loggerFactory = LoggerFactory.Create(builder =>
        {
            builder
                .AddConsole()
                .SetMinimumLevel(LogLevel.Information);
        });

        var logger = loggerFactory.CreateLogger<Program>();

        // Setup dependency injection
        var services = new ServiceCollection();
        services.AddSingleton<IConfiguration>(configuration);
        services.AddLogging(builder => builder.AddConsole().SetMinimumLevel(LogLevel.Information));
        
        // Add HttpClient for OpenAI service
        services.AddHttpClient<OpenAIEmbeddingService>();
        services.AddSingleton<ExcelService>();
        services.AddSingleton<DatabaseService>();

        var serviceProvider = services.BuildServiceProvider();

        // Get services
        var excelService = serviceProvider.GetRequiredService<ExcelService>();
        var embeddingService = serviceProvider.GetRequiredService<OpenAIEmbeddingService>();
        var databaseService = serviceProvider.GetRequiredService<DatabaseService>();

        try
        {
            logger.LogInformation("=== Excel to Vector Importer ===");
            logger.LogInformation("Starting import process...\n");

            // Get Excel file path from command line or use default
            var excelFilePath = args.Length > 0 ? args[0] : "Products.xlsx";
            
            if (!File.Exists(excelFilePath))
            {
                logger.LogError("Excel file not found: {FilePath}", excelFilePath);
                logger.LogInformation("Usage: ExcelToVectorImporter.exe [path-to-Products.xlsx]");
                return;
            }

            logger.LogInformation("Excel file: {FilePath}", excelFilePath);

            // Step 1: Test database connection
            logger.LogInformation("\n[Step 1/5] Testing database connection...");
            var connectionOk = await databaseService.TestConnectionAsync();
            if (!connectionOk)
            {
                logger.LogError("Database connection failed. Please check your connection string and ensure the table exists.");
                logger.LogInformation("Run the SQL script 'CreateProductsHybridTable.sql' first to create the table.");
                return;
            }
            logger.LogInformation("✓ Database connection successful");

            // Step 2: Read Excel file
            logger.LogInformation("\n[Step 2/5] Reading Excel file...");
            var products = await excelService.ReadProductsFromExcelAsync(excelFilePath);
            logger.LogInformation("✓ Read {Count} products from Excel", products.Count);

            if (products.Count == 0)
            {
                logger.LogWarning("No products found in Excel file. Exiting.");
                return;
            }

            // Step 3: Generate embeddings
            logger.LogInformation("\n[Step 3/5] Generating embeddings using OpenAI API...");
            logger.LogInformation("This may take a while depending on the number of products...");

            var batchSize = int.Parse(configuration["Processing:BatchSize"] ?? "50");
            var totalBatches = (int)Math.Ceiling(products.Count / (double)batchSize);
            var processedCount = 0;

            for (int i = 0; i < products.Count; i += batchSize)
            {
                var batch = products.Skip(i).Take(batchSize).ToList();
                var batchNumber = (i / batchSize) + 1;

                logger.LogInformation("Processing batch {BatchNumber}/{TotalBatches} ({Count} products)...", 
                    batchNumber, totalBatches, batch.Count);

                // Build text contexts for embedding
                var texts = batch.Select(p => p.FullTextContext).ToList();

                try
                {
                    // Generate embeddings for the batch
                    var embeddings = await embeddingService.GenerateEmbeddingsBatchAsync(texts);

                    // Assign embeddings to products
                    for (int j = 0; j < batch.Count && j < embeddings.Count; j++)
                    {
                        batch[j].Embedding = embeddings[j];
                    }

                    processedCount += batch.Count;
                    logger.LogInformation("✓ Generated embeddings for batch {BatchNumber} ({ProcessedCount}/{TotalCount})", 
                        batchNumber, processedCount, products.Count);

                    // Small delay to avoid rate limits
                    if (i + batchSize < products.Count)
                    {
                        await Task.Delay(500); // 500ms delay between batches
                    }
                }
                catch (Exception ex)
                {
                    logger.LogError(ex, "Error generating embeddings for batch {BatchNumber}", batchNumber);
                    throw;
                }
            }

            logger.LogInformation("✓ Generated embeddings for all {Count} products", products.Count);

            // Step 4: Insert into database
            logger.LogInformation("\n[Step 4/5] Inserting products into SQL Server...");

            var productsWithEmbeddings = products.Where(p => p.Embedding != null && p.Embedding.Length > 0).ToList();
            logger.LogInformation("Inserting {Count} products with embeddings...", productsWithEmbeddings.Count);

            var insertBatchSize = batchSize; // Use same batch size for inserts
            var totalInsertBatches = (int)Math.Ceiling(productsWithEmbeddings.Count / (double)insertBatchSize);
            var insertedCount = 0;

            for (int i = 0; i < productsWithEmbeddings.Count; i += insertBatchSize)
            {
                var batch = productsWithEmbeddings.Skip(i).Take(insertBatchSize).ToList();
                var batchNumber = (i / insertBatchSize) + 1;

                logger.LogInformation("Inserting batch {BatchNumber}/{TotalBatches}...", batchNumber, totalInsertBatches);

                try
                {
                    var count = await databaseService.InsertProductsBatchAsync(batch);
                    insertedCount += count;
                    logger.LogInformation("✓ Inserted batch {BatchNumber} ({InsertedCount}/{TotalCount})", 
                        batchNumber, insertedCount, productsWithEmbeddings.Count);
                }
                catch (Exception ex)
                {
                    logger.LogError(ex, "Error inserting batch {BatchNumber}", batchNumber);
                    throw;
                }
            }

            logger.LogInformation("✓ Successfully inserted {Count} products into database", insertedCount);

            // Step 5: Verify
            logger.LogInformation("\n[Step 5/5] Verifying import...");
            var totalCount = await databaseService.GetProductCountAsync();
            logger.LogInformation("✓ Total products in database: {Count}", totalCount);

            logger.LogInformation("\n=== Import completed successfully! ===");
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Fatal error during import process");
            Environment.ExitCode = 1;
        }
    }
}
