#!/usr/bin/env python3
"""
Comprehensive test script for the Bookwyrm's Hoard FastAPI web API.
Tests all endpoints with proper test data isolation.
"""

import sys
import requests
from typing import Dict, Any, List

def test_api_endpoint(url: str, method: str = "GET", data: Dict[str, Any] = None, expected_status: int = 200) -> bool:
    """Test an API endpoint and return True if successful."""
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=data, headers=headers, timeout=5)
        elif method == "DELETE":
            response = requests.delete(url, timeout=5)
        else:
            print(f"❌ Unsupported method: {method}")
            return False
            
        if response.status_code == expected_status:
            print(f"✅ {method} {url} - Status: {response.status_code}")
            # Add helpful context for different response types
            if expected_status == 200:
                try:
                    json_data = response.json()
                    if method == "GET" and isinstance(json_data, list):
                        print(f"   📋 Returned {len(json_data)} items")
                        if json_data and "book_info" in json_data[0]:
                            print(f"   📖 First book: {json_data[0]['book_info']['title']}")
                        elif json_data and "name" in json_data[0]:
                            print(f"   🏗️  First shelf: {json_data[0]['location']}/{json_data[0]['name']}")
                    elif isinstance(json_data, dict):
                        if "book_info" in json_data:
                            title = json_data['book_info']['title']
                            location = json_data.get('home_location')
                            if location:
                                print(f"   📖 Book: {title} at {location['location']}/{location['bookshelf_name']}")
                            else:
                                print(f"   📖 Book: {title} (not in library)")
                        elif "name" in json_data:
                            print(f"   🏗️  Shelf: {json_data['location']}/{json_data['name']} ({json_data['columns']}x{json_data['rows']})")
                        elif "message" in json_data:
                            print(f"   💬 Message: {json_data['message']}")
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
    """Comprehensive test of all API endpoints using test data."""
    base_url = "http://localhost:8000"
    
    print("🧪 COMPREHENSIVE Bookwyrm's Hoard API Test with TEST DATA")
    print("=" * 70)
    
    all_passed = True
    
    # Test system endpoints
    print("\n🔧 System Endpoints:")
    system_tests = [
        (f"{base_url}/", "GET", None, 200),
        (f"{base_url}/api/health", "GET", None, 200),
        (f"{base_url}/docs", "GET", None, 200),  # FastAPI docs
    ]
    
    for url, method, data, expected in system_tests:
        if not test_api_endpoint(url, method, data, expected):
            all_passed = False
    
    # Test book search and retrieval
    print("\n📚 Book Search & Retrieval:")
    book_search_tests = [
        (f"{base_url}/api/books", "GET", None, 200),  # Get all books
        (f"{base_url}/api/books?q=python", "GET", None, 200),  # Smart search by title/author
        (f"{base_url}/api/books?q=9780134685991", "GET", None, 200),  # Smart search by ISBN
        (f"{base_url}/api/books?q=effective", "GET", None, 200),  # Smart search text
        (f"{base_url}/api/books/9780134685991", "GET", None, 200),  # Get existing book
        (f"{base_url}/api/books/NONEXISTENT", "GET", None, 404),  # Get non-existent book
    ]
    
    for url, method, data, expected in book_search_tests:
        if not test_api_endpoint(url, method, data, expected):
            all_passed = False
    
    # Test the new lookup endpoint
    print("\n🔍 Book Lookup (New Endpoint):")
    lookup_tests = [
        (f"{base_url}/api/lookup/9780134685991", "GET", None, 200),  # Book in library
        (f"{base_url}/api/lookup/9780321356680", "GET", None, 200),  # Book not in library (external lookup)
        (f"{base_url}/api/lookup/INVALIDISBN12345", "GET", None, 404),  # Invalid ISBN
    ]
    
    for url, method, data, expected in lookup_tests:
        if not test_api_endpoint(url, method, data, expected):
            all_passed = False
    
    # Test book addition
    print("\n➕ Book Addition:")
    
    # Test 1: Add book with manual entry and explicit ISBN
    manual_book = {
        "isbn": "TEST-DUPLICATE-123",  # Use explicit ISBN for duplicate testing
        "title": "API Test Book",
        "authors": ["API Tester"], 
        "publisher": "Test Publisher",
        "location": "Library",
        "bookshelf_name": "Test Shelf",
        "column": 1,
        "row": 2,
        "notes": "Added via API test"
    }
    
    # First add the book
    if test_api_endpoint(f"{base_url}/api/books", "POST", manual_book, 200):
        print("   📋 Book added successfully")
        # Now try to add duplicate (should fail)
        if not test_api_endpoint(f"{base_url}/api/books", "POST", manual_book, 400):
            all_passed = False
            print("   ⚠️  Expected duplicate book addition to fail")
        else:
            print("   📋 Duplicate addition properly rejected")
    else:
        all_passed = False
    
    # Test 2: Add book with invalid data
    invalid_book = {
        "isbn": "invalid-isbn",
        # No title - should fail
    }
    
    if not test_api_endpoint(f"{base_url}/api/books", "POST", invalid_book, 400):
        all_passed = False
    
    # Test checkout/checkin workflow
    print("\n📤📥 Checkout/Checkin Workflow:")
    test_isbn = "9780134685991"  # Effective Python
    checkout_data = {"checked_out_to": "Comprehensive Tester"}
    
    checkout_tests = [
        # Test checkout
        (f"{base_url}/api/books/{test_isbn}/checkout", "POST", checkout_data, 200),
        # Test checkout of already checked out book (should fail)
        (f"{base_url}/api/books/{test_isbn}/checkout", "POST", checkout_data, 400),
        # Test simple checkin
        (f"{base_url}/api/books/{test_isbn}/checkin", "POST", None, 200),
    ]
    
    for url, method, data, expected in checkout_tests:
        if not test_api_endpoint(url, method, data, expected):
            all_passed = False
    
    # Test checkout with relocation
    print("\n🔄 Checkout with Relocation:")
    
    # Check out again for relocation test
    if test_api_endpoint(f"{base_url}/api/books/{test_isbn}/checkout", "POST", checkout_data, 200):
        relocation_data = {
            "location": "Library",
            "bookshelf_name": "Test Shelf",
            "column": 1,
            "row": 1
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
            # Check out and reset
            test_api_endpoint(f"{base_url}/api/books/{test_isbn}/checkout", "POST", checkout_data, 200)
            test_api_endpoint(f"{base_url}/api/books/{test_isbn}/checkin", "POST", reset_data, 200)
            print("   📋 Book reset to original location")
        else:
            all_passed = False
    else:
        all_passed = False
    
    # Test shelf management
    print("\n🏗️  Shelf Management:")
    
    shelf_tests = [
        # Get all shelves
        (f"{base_url}/api/shelves", "GET", None, 200),
        # Get specific shelf
        (f"{base_url}/api/shelves/Library/Test Shelf", "GET", None, 200),
        # Get non-existent shelf
        (f"{base_url}/api/shelves/NonExistent/Fake Shelf", "GET", None, 404),
    ]
    
    for url, method, data, expected in shelf_tests:
        if not test_api_endpoint(url, method, data, expected):
            all_passed = False
    
    # Test shelf creation and deletion
    print("\n🔨 Shelf Creation & Deletion:")
    
    test_shelf_data = {
        "location": "Test Room",
        "name": "Comprehensive Test Shelf",
        "rows": 3,
        "columns": 4,
        "description": "Created by comprehensive API test"
    }
    
    shelf_crud_tests = [
        # Create shelf
        (f"{base_url}/api/shelves", "POST", test_shelf_data, 200),
        # Verify shelf exists
        (f"{base_url}/api/shelves/Test Room/Comprehensive Test Shelf", "GET", None, 200),
        # Try to create duplicate (should fail)
        (f"{base_url}/api/shelves", "POST", test_shelf_data, 400),
        # Delete shelf
        (f"{base_url}/api/shelves/Test Room/Comprehensive Test Shelf", "DELETE", None, 200),
        # Verify shelf is gone
        (f"{base_url}/api/shelves/Test Room/Comprehensive Test Shelf", "GET", None, 404),
        # Try to delete non-existent shelf
        (f"{base_url}/api/shelves/NonExistent/Fake Shelf", "DELETE", None, 404),
    ]
    
    for url, method, data, expected in shelf_crud_tests:
        if not test_api_endpoint(url, method, data, expected):
            all_passed = False
    
    # Test shelf validation
    print("\n❌ Shelf Validation Tests:")
    
    invalid_shelf_data = {
        "location": "Test Room",
        "name": "Invalid Shelf",
        "rows": 0,  # Invalid - must be positive
        "columns": 5,
        "description": "This should fail"
    }
    
    if not test_api_endpoint(f"{base_url}/api/shelves", "POST", invalid_shelf_data, 400):
        all_passed = False
    
    # Test shelf deletion protection (try to delete shelf with books)
    print("\n🛡️  Shelf Protection Tests:")
    
    if not test_api_endpoint(f"{base_url}/api/shelves/Library/Test Shelf", "DELETE", None, 400):
        all_passed = False
        print("   ⚠️  Expected shelf deletion to fail due to books on shelf")
    else:
        print("   📋 Shelf deletion properly blocked (shelf has books)")
    
    # Error scenario tests
    print("\n❌ Additional Error Scenarios:")
    
    error_tests = [
        # Try to check out pre-checked-out book
        (f"{base_url}/api/books/CHECKED456789/checkout", "POST", {"checked_out_to": "Tester"}, 400),
        # Try to check in book that's not checked out
        (f"{base_url}/api/books/TEST123456789/checkin", "POST", None, 400),
        # Try to add book to non-existent shelf
        (f"{base_url}/api/books", "POST", {
            "title": "Bad Shelf Book",
            "authors": ["Test"],
            "location": "NonExistent",
            "bookshelf_name": "Fake Shelf",
            "column": 0,
            "row": 0
        }, 400),
    ]
    
    for url, method, data, expected in error_tests:
        if not test_api_endpoint(url, method, data, expected):
            all_passed = False
    
    # Summary
    print("=" * 70)
    if all_passed:
        print("🎉 ALL COMPREHENSIVE API TESTS PASSED!")
        print("✅ Your complete library management API is working perfectly")
        print("📊 Tested endpoints:")
        print("   • System: Root, Health, Docs")
        print("   • Books: Search, Get, Add, Lookup, Checkout, Checkin")  
        print("   • Shelves: List, Get, Create, Delete")
        print("   • Error handling: All edge cases covered")
    else:
        print("⚠️  Some API tests failed. Check the server logs.")
        sys.exit(1)

if __name__ == "__main__":
    print("📋 IMPORTANT: Make sure you've switched to test data:")
    print("   ./switch_data.sh test")
    print("📋 Make sure the API server is running:")
    print("   python main.py web --reload")
    print("📋 This test will:")
    print("   • Test all 12+ API endpoints")
    print("   • Verify error handling")
    print("   • Test the new lookup endpoint")
    print("   • Test book addition")
    print("   • Test complete shelf management")
    print()
    input("Press Enter when ready to run comprehensive tests...")
    main()