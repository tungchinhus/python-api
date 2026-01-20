using System.Globalization;
using ExcelToVectorImporter.Models;
using Microsoft.Extensions.Logging;
using OfficeOpenXml;

namespace ExcelToVectorImporter.Services;

public class ExcelService
{
    private readonly ILogger<ExcelService> _logger;

    public ExcelService(ILogger<ExcelService> logger)
    {
        _logger = logger;
        // Set EPPlus license context (required for EPPlus 7+)
        ExcelPackage.LicenseContext = LicenseContext.NonCommercial; // Change to Commercial if needed
    }

    /// <summary>
    /// Reads products from Excel file
    /// </summary>
    public async Task<List<Product>> ReadProductsFromExcelAsync(string filePath)
    {
        if (!File.Exists(filePath))
            throw new FileNotFoundException($"Excel file not found: {filePath}");

        var products = new List<Product>();

        try
        {
            using var package = new ExcelPackage(new FileInfo(filePath));
            var worksheet = package.Workbook.Worksheets[0]; // First worksheet

            if (worksheet == null)
                throw new InvalidOperationException("Excel file does not contain any worksheets");

            // Read header row to find column indices
            var headerRow = 1;
            var headers = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
            
            for (int col = 1; col <= worksheet.Dimension?.End.Column; col++)
            {
                var headerValue = worksheet.Cells[headerRow, col].GetValue<string>();
                if (!string.IsNullOrWhiteSpace(headerValue))
                {
                    headers[headerValue.Trim()] = col;
                }
            }

            _logger.LogInformation("Found headers: {Headers}", string.Join(", ", headers.Keys));

            // Validate required columns
            var requiredColumns = new[] { "ProductId", "ProductName" };
            foreach (var requiredCol in requiredColumns)
            {
                if (!headers.ContainsKey(requiredCol))
                    throw new InvalidOperationException(
                        $"Required column '{requiredCol}' not found in Excel file");
            }

            // Read data rows
            var startRow = 2; // Data starts from row 2 (row 1 is header)
            var endRow = worksheet.Dimension?.End.Row ?? startRow;

            for (int row = startRow; row <= endRow; row++)
            {
                // Skip empty rows
                if (worksheet.Cells[row, headers["ProductId"]].GetValue<string>() == null)
                    continue;

                var product = new Product
                {
                    ProductId = GetCellValue<string>(worksheet, row, headers, "ProductId") ?? string.Empty,
                    ProductName = GetCellValue<string>(worksheet, row, headers, "ProductName") ?? string.Empty,
                    Category = GetCellValue<string>(worksheet, row, headers, "Category"),
                    Description = GetCellValue<string>(worksheet, row, headers, "Description"),
                    Price = GetCellValue<decimal?>(worksheet, row, headers, "Price"),
                    StockQuantity = GetCellValue<int?>(worksheet, row, headers, "StockQuantity"),
                    LastUpdated = GetCellValue<DateTime?>(worksheet, row, headers, "LastUpdated")
                };

                // Build full text context
                product.FullTextContext = product.BuildFullTextContext();

                if (string.IsNullOrWhiteSpace(product.ProductId) || string.IsNullOrWhiteSpace(product.ProductName))
                {
                    _logger.LogWarning("Skipping row {Row} due to missing ProductId or ProductName", row);
                    continue;
                }

                products.Add(product);
            }

            _logger.LogInformation("Read {Count} products from Excel file: {FilePath}", products.Count, filePath);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error reading Excel file: {FilePath}", filePath);
            throw;
        }

        return await Task.FromResult(products);
    }

    private T? GetCellValue<T>(ExcelWorksheet worksheet, int row, Dictionary<string, int> headers, string columnName)
    {
        if (!headers.TryGetValue(columnName, out var col))
            return default;

        var cellValue = worksheet.Cells[row, col].Value;
        
        if (cellValue == null)
            return default;

        try
        {
            // Handle different types
            if (typeof(T) == typeof(string))
                return (T)(object)cellValue.ToString()!;
            
            if (typeof(T) == typeof(int?))
            {
                if (cellValue is double d)
                    return (T)(object)(int)d;
                if (int.TryParse(cellValue.ToString(), out var intVal))
                    return (T)(object)intVal;
                return default;
            }
            
            if (typeof(T) == typeof(decimal?))
            {
                if (cellValue is double d)
                    return (T)(object)(decimal)d;
                if (decimal.TryParse(cellValue.ToString(), NumberStyles.Any, CultureInfo.InvariantCulture, out var decVal))
                    return (T)(object)decVal;
                return default;
            }
            
            if (typeof(T) == typeof(DateTime?))
            {
                if (cellValue is DateTime dt)
                    return (T)(object)dt;
                if (DateTime.TryParse(cellValue.ToString(), out var dateVal))
                    return (T)(object)dateVal;
                return default;
            }

            return (T)Convert.ChangeType(cellValue, typeof(T));
        }
        catch
        {
            return default;
        }
    }
}
