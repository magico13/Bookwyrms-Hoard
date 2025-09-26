#!/usr/bin/env python3
"""
Enhanced test script for the Bookwyrms-Hoard FastAPI web API.
Uses test data to avoid modifying production library data.
"""

import sys
import requests
import json
from typing import Dict, Any

def test_api_endpoint(url: str, method: str = "GET", data: Dict[str, Any] = None, expected_status: int = 200) -> bool:
    """Test an API endpoint and return True if successful."""
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=data, headers=headers, timeout=5)
        else:
            print(f"❌ Unsupported method: {method}")
            return False
            
        if response.status_code == expected_status:
            print(f"✅ {method} {url} - Status: {response.status_code}")
            if expected_status == 200 and method == "GET":
                try:
                    json_data = response.json()
                    if isinstance(json_data, list):
                        print(f"   📋 Returned {len(json_data)} items")
                    elif isinstance(json_data, dict) and "book_info" in json_data:
                        print(f"   📖 Book: {json_data['book_info']['title']}")
                except:
                    pass
            return True
        else:
            print(f"❌ {method} {url} - Status: {response.status_code} (expected {expected_status})")
            try:
                error_detail = response.json().get("detail", "No detail")
                print(f"   Error: {error_detail}")
            except:
                pass
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ {method} {url} - Error: {e}")
        return False

def main() -> None:
    """Test the web API endpoints using test data."""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Bookwyrms-Hoard Web API with TEST DATA")
    print("=" * 60)
    
    # Test basic endpoints
    print("\n📋 Basic Endpoints:")
    all_passed = True
    
    basic_tests = [
        (f"{base_url}/", "GET", None, 200),
        (f"{base_url}/api/health", "GET", None, 200),
        (f"{base_url}/api/books", "GET", None, 200),  # Get all books
        (f"{base_url}/docs", "GET", None, 200),  # FastAPI docs
    ]
    
    for url, method, data, expected in basic_tests:
        if not test_api_endpoint(url, method, data, expected):
            all_passed = False
    
    # Test search functionality
    print("\n🔍 Search Tests:")
    search_tests = [
        (f"{base_url}/api/books?title=python", "GET", None, 200),
        (f"{base_url}/api/books?author=slatkin", "GET", None, 200),
        (f"{base_url}/api/books?title=algorithms&author=cormen", "GET", None, 200),
    ]
    
    for url, method, data, expected in search_tests:
        if not test_api_endpoint(url, method, data, expected):
            all_passed = False
    
    # Test individual book lookup
    print("\n📖 Book Lookup Tests:")
    book_tests = [
        (f"{base_url}/api/books/9780134685991", "GET", None, 200),  # Effective Python
        (f"{base_url}/api/books/TEST123456789", "GET", None, 200),   # Test book
        (f"{base_url}/api/books/NONEXISTENT", "GET", None, 404),     # Should fail
    ]
    
    for url, method, data, expected in book_tests:
        if not test_api_endpoint(url, method, data, expected):
            all_passed = False
    
    # Test checkout/checkin workflow
    print("\n📤📥 Checkout/Checkin Tests:")
    test_isbn = "9780134685991"  # Effective Python
    
    # Test checkout
    checkout_data = {"checked_out_to": "API Tester"}
    if test_api_endpoint(f"{base_url}/api/books/{test_isbn}/checkout", "POST", checkout_data, 200):
        print("   📋 Book checked out successfully")
        
        # Test checkout of already checked out book (should fail)
        test_api_endpoint(f"{base_url}/api/books/{test_isbn}/checkout", "POST", checkout_data, 400)
        
        # Test simple checkin
        if test_api_endpoint(f"{base_url}/api/books/{test_isbn}/checkin", "POST", None, 200):
            print("   📋 Book checked in successfully")
        else:
            all_passed = False
    else:
        all_passed = False
    
    # Test checkout with relocation
    print("\n🔄 Relocation Tests:")
    if test_api_endpoint(f"{base_url}/api/books/{test_isbn}/checkout", "POST", checkout_data, 200):
        # Test checkin with relocation
        relocation_data = {
            "location": "Library",
            "bookshelf_name": "Test Shelf",
            "column": 1,
            "row": 2
        }
        if test_api_endpoint(f"{base_url}/api/books/{test_isbn}/checkin", "POST", relocation_data, 200):
            print("   📋 Book relocated successfully")
            
            # Reset to original location
            reset_data = {
                "location": "Library", 
                "bookshelf_name": "Test Shelf",
                "column": 0,
                "row": 0
            }
            test_api_endpoint(f"{base_url}/api/books/{test_isbn}/checkout", "POST", checkout_data, 200)
            test_api_endpoint(f"{base_url}/api/books/{test_isbn}/checkin", "POST", reset_data, 200)
            print("   📋 Book reset to original location")
        else:
            all_passed = False
    
    # Test error scenarios
    print("\n❌ Error Scenario Tests:")
    error_tests = [
        # Try to check out pre-checked-out book
        (f"{base_url}/api/books/CHECKED456789/checkout", "POST", {"checked_out_to": "Tester"}, 400),
        # Try to check in book that's not checked out
        (f"{base_url}/api/books/TEST123456789/checkin", "POST", None, 400),
        # Try invalid shelf location
        (f"{base_url}/api/books/{test_isbn}/checkout", "POST", checkout_data, 200),  # First check out
    ]
    
    # Check out a book first for the invalid location test
    requests.post(f"{base_url}/api/books/{test_isbn}/checkout", json=checkout_data)
    
    invalid_location = {
        "location": "NonExistent",
        "bookshelf_name": "Fake Shelf", 
        "column": 0,
        "row": 0
    }
    test_api_endpoint(f"{base_url}/api/books/{test_isbn}/checkin", "POST", invalid_location, 400)
    
    # Clean up - check in the book normally
    requests.post(f"{base_url}/api/books/{test_isbn}/checkin")
    
    print("=" * 60)
    if all_passed:
        print("🎉 All API tests passed!")
        print("✅ Your API is working correctly with test data")
    else:
        print("⚠️  Some API tests failed. Check the server logs.")
        sys.exit(1)

if __name__ == "__main__":
    print("📋 Make sure you've switched to test data:")
    print("   ./switch_data.sh test")
    print("📋 Make sure the API server is running:")
    print("   python main.py web --reload")
    print()
    input("Press Enter when ready to run tests...")
    main()