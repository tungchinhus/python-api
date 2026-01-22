"""
Script kiểm tra các services đang chạy
Chạy: python check_services.py
"""

import requests
import sys
from datetime import datetime

def check_service(name, url, timeout=5):
    """Kiểm tra một service"""
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            print(f"✅ {name}: OK")
            if data:
                print(f"   Status: {data.get('status', 'OK')}")
            return True
        else:
            print(f"⚠️ {name}: HTTP {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ {name}: Connection refused (service not running)")
        return False
    except requests.exceptions.Timeout:
        print(f"⏱️ {name}: Timeout (service may be starting)")
        return False
    except Exception as e:
        print(f"❌ {name}: {str(e)}")
        return False

def main():
    """Kiểm tra tất cả services"""
    print("=" * 60)
    print("CHECKING SERVICES")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    services = [
        ("Python API", "http://localhost:5005/health"),
        ("RAG API", "http://localhost:8000/health"),
    ]
    
    results = []
    for name, url in services:
        result = check_service(name, url)
        results.append((name, result))
        print()
    
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_ok = all(result for _, result in results)
    
    if all_ok:
        print("✅ All services are running!")
        print()
        print("You can now:")
        print("  - Test chat: python test_chat_table.py")
        print("  - Test suggestions: python test_suggestions.py")
    else:
        print("❌ Some services are not running!")
        print()
        print("To start services:")
        print("  - Run: start_all.bat")
        print("  - Or manually:")
        print("    1. python app.py (Python API)")
        print("    2. python rag_main_sql.py (RAG API)")
        print()
        print("See START_SERVICES.md for details.")
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
