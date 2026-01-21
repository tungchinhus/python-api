"""
Test script để kiểm tra endpoint /api/search/vector
"""
import requests
import json

def test_vector_search():
    """Test vector search endpoint"""
    url = "http://localhost:5000/api/search/vector"
    
    # Test data
    test_data = {
        "query": "Tầm nhìn 2035: THIBIDI trở thành số #1",
        "tableName": "rag_documents",
        "topN": 5,
        "similarityThreshold": 0.3
    }
    
    print(f"Testing POST {url}")
    print(f"Request data: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, json=test_data, timeout=30)
        
        print(f"\nResponse status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"SUCCESS!")
            print(f"Results: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"ERROR {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
            except:
                print(f"Error text: {response.text}")
                
    except requests.exceptions.ConnectionError:
        print("Connection Error: Khong the ket noi den http://localhost:5000")
        print("   Dam bao Python API server dang chay: python app.py")
    except requests.exceptions.Timeout:
        print("Timeout: Request qua lau")
    except Exception as e:
        print(f"Unexpected error: {e}")

def test_health():
    """Test health endpoint"""
    url = "http://localhost:5000/api/search/health"
    
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
        print("Connection Error: Khong the ket noi den http://localhost:5000")
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
    
    # Test vector search
    test_vector_search()
    
    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60)
