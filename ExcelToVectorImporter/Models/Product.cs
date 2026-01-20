namespace ExcelToVectorImporter.Models;

public class Product
{
    public string ProductId { get; set; } = string.Empty;
    public string ProductName { get; set; } = string.Empty;
    public string? Category { get; set; }
    public string? Description { get; set; }
    public decimal? Price { get; set; }
    public int? StockQuantity { get; set; }
    public DateTime? LastUpdated { get; set; }
    
    // Computed properties
    public string FullTextContext { get; set; } = string.Empty;
    public float[]? Embedding { get; set; }
    
    /// <summary>
    /// Constructs the full text context for embedding generation
    /// Format: "Product: {ProductName}. Category: {Category}. Description: {Description}. Price: {Price}."
    /// </summary>
    public string BuildFullTextContext()
    {
        var parts = new List<string>();
        
        if (!string.IsNullOrWhiteSpace(ProductName))
            parts.Add($"Product: {ProductName}");
        
        if (!string.IsNullOrWhiteSpace(Category))
            parts.Add($"Category: {Category}");
        
        if (!string.IsNullOrWhiteSpace(Description))
            parts.Add($"Description: {Description}");
        
        if (Price.HasValue)
            parts.Add($"Price: {Price.Value:C}");
        
        return string.Join(". ", parts) + ".";
    }
}
