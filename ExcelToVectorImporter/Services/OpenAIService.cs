using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;

namespace ExcelToVectorImporter.Services;

public class OpenAIEmbeddingService
{
    private readonly ILogger<OpenAIEmbeddingService> _logger;
    private readonly HttpClient _httpClient;
    private readonly string _apiKey;
    private readonly string _model;
    private readonly int _dimensions;

    public OpenAIEmbeddingService(IConfiguration configuration, ILogger<OpenAIEmbeddingService> logger, HttpClient httpClient)
    {
        _logger = logger;
        _httpClient = httpClient;
        
        _apiKey = configuration["OpenAI:ApiKey"] 
            ?? throw new InvalidOperationException("OpenAI:ApiKey is not configured in appsettings.json");
        
        _model = configuration["OpenAI:Model"] ?? "text-embedding-3-small";
        _dimensions = int.Parse(configuration["OpenAI:Dimensions"] ?? "1536");
        
        // Set up HTTP client for OpenAI API
        _httpClient.BaseAddress = new Uri("https://api.openai.com/v1/");
        _httpClient.DefaultRequestHeaders.Add("Authorization", $"Bearer {_apiKey}");
    }

    /// <summary>
    /// Generates an embedding for the given text using OpenAI API
    /// </summary>
    public async Task<float[]> GenerateEmbeddingAsync(string text, CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(text))
            throw new ArgumentException("Text cannot be null or empty", nameof(text));

        var embeddings = await GenerateEmbeddingsBatchAsync(new List<string> { text }, cancellationToken);
        return embeddings.FirstOrDefault() ?? throw new InvalidOperationException("Failed to generate embedding");
    }

    /// <summary>
    /// Generates embeddings for multiple texts in batch
    /// </summary>
    public async Task<List<float[]>> GenerateEmbeddingsBatchAsync(
        List<string> texts, 
        CancellationToken cancellationToken = default)
    {
        if (texts == null || texts.Count == 0)
            return new List<float[]>();

        var embeddings = new List<float[]>();
        
        // Process in batches to avoid rate limits
        const int batchSize = 100; // OpenAI allows up to 2048 inputs per request, but we use smaller batches
        
        for (int i = 0; i < texts.Count; i += batchSize)
        {
            var batch = texts.Skip(i).Take(batchSize).ToList();
            
            try
            {
                var requestBody = new
                {
                    model = _model,
                    input = batch,
                    dimensions = _dimensions
                };

                var jsonContent = JsonSerializer.Serialize(requestBody);
                var content = new StringContent(jsonContent, Encoding.UTF8, "application/json");

                var response = await _httpClient.PostAsync("embeddings", content, cancellationToken);
                response.EnsureSuccessStatusCode();

                var responseContent = await response.Content.ReadAsStringAsync(cancellationToken);
                var jsonDoc = JsonDocument.Parse(responseContent);
                var root = jsonDoc.RootElement;

                if (!root.TryGetProperty("data", out var dataArray))
                    throw new InvalidOperationException("No 'data' property in OpenAI API response");

                foreach (var item in dataArray.EnumerateArray())
                {
                    if (!item.TryGetProperty("embedding", out var embeddingArray))
                        throw new InvalidOperationException("No 'embedding' property in response item");

                    var embedding = new List<float>();
                    foreach (var value in embeddingArray.EnumerateArray())
                    {
                        embedding.Add((float)value.GetDouble());
                    }

                    if (embedding.Count != _dimensions)
                        throw new InvalidOperationException(
                            $"Expected embedding dimension {_dimensions}, but got {embedding.Count}");

                    embeddings.Add(embedding.ToArray());
                }

                _logger.LogInformation("Generated {Count} embeddings (batch {BatchNumber})", 
                    batch.Count, (i / batchSize) + 1);
                
                // Small delay to avoid rate limits
                if (i + batchSize < texts.Count)
                    await Task.Delay(100, cancellationToken);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error generating embeddings for batch starting at index {Index}", i);
                throw;
            }
        }

        return embeddings;
    }
}
