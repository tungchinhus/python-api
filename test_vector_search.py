"""
Test script để kiểm tra endpoint /api/search/vector
"""
import requests
import json

def test_vector_search(table_name="rag_documents", query=None):
    """Test vector search endpoint"""
    url = "http://localhost:5005/api/search/vector"
    
    if query is None:
        query = "Tầm nhìn 2035: THIBIDI trở thành số #1"
    
    # Test data
    test_data = {
        "query": query,
        "tableName": table_name,
        "topN": 5,
        "similarityThreshold": 0.3
    }
    
    print(f"\n{'='*60}")
    print(f"Testing POST {url}")
    print(f"Table: {table_name}")
    print(f"Query: {query}")
    print(f"{'='*60}")
    print(f"Request data: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, json=test_data, timeout=30)
        
        print(f"\nResponse status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ SUCCESS!")
            print(f"Total results: {result.get('totalResults', 0)}")
            
            if result.get('warning'):
                print(f"⚠️  Warning: {result.get('warning')}")
            
            if result.get('results'):
                print(f"\nTop {len(result['results'])} results:")
                for i, r in enumerate(result['results'][:3], 1):
                    print(f"  {i}. ID={r.get('id')}, Similarity={r.get('similarity', 0):.4f}")
                    content_preview = r.get('content', '')[:100]
                    print(f"     Content: {content_preview}...")
            else:
                print("⚠️  No results found!")
                print(f"Full response: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"\n❌ ERROR {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
            except:
                print(f"Error text: {response.text}")
                
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection Error: Khong the ket noi den http://localhost:5005")
        print("   Dam bao Python API server dang chay: python app.py")
        print("   Hoac kiem tra PORT trong .env file")
    except requests.exceptions.Timeout:
        print("\n❌ Timeout: Request qua lau (>30s)")
        print("   Co the database co qua nhieu du lieu hoac connection cham")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

def test_health():
    """Test health endpoint"""
    url = "http://localhost:5005/api/search/health"
    
    print(f"\nTesting GET {url}")
    
    try:
        response = requests.get(url, timeout=5)
        print(f"Response status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Health check: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"Error: {response.text}")
    except requests.exceptions.ConnectionError:
        print("Connection Error: Khong the ket noi den http://localhost:5005")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import sys
    import io
    # Fix encoding for Windows console
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    print("=" * 60)
    print("Testing Vector Search API")
    print("=" * 60)
    
    # Test health first
    test_health()
    
    # Test vector search với rag_documents
    test_vector_search("rag_documents")
    
    # Test vector search với TSMay (table mà user đang dùng)
    test_vector_search("TSMay", "TBKT")
    
    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60)
    print("\n💡 Tips:")
    print("  - Nếu không tìm thấy kết quả, kiểm tra:")
    print("    1. Bảng có tồn tại không?")
    print("    2. Bảng có cột Embedding hoặc VectorJson không?")
    print("    3. Bảng có dữ liệu với embeddings không?")
    print("    4. Chạy: python test_sql_connection.py để kiểm tra DB connection")
    print("    5. Chạy: python debug_api.py để debug chi tiết")