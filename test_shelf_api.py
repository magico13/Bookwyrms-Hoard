#!/usr/bin/env python3
"""
Test script for the shelf management API endpoints.
Uses test data to avoid modifying production library data.
"""

import sys
import requests
import json
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
            if expected_status == 200 and method == "GET":
                try:
                    json_data = response.json()
                    if isinstance(json_data, list):
                        print(f"   📋 Returned {len(json_data)} items")
                        if json_data and "name" in json_data[0]:
                            print(f"   🏗️  First shelf: {json_data[0]['location']}/{json_data[0]['name']}")
                    elif isinstance(json_data, dict) and "name" in json_data:
                        print(f"   🏗️  Shelf: {json_data['location']}/{json_data['name']} ({json_data['columns']}x{json_data['rows']})")
                except:
                    pass
            elif expected_status == 200 and method == "POST":
                try:
                    json_data = response.json()
                    if "name" in json_data:
                        print(f"   🏗️  Created: {json_data['location']}/{json_data['name']} ({json_data['columns']}x{json_data['rows']})")
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
    """Test the shelf API endpoints using test data."""
    base_url = "http://localhost:8000"
    
    print("🏗️  Testing Bookwyrms-Hoard Shelf API with TEST DATA")
    print("=" * 60)
    
    # Test getting all shelves
    print("\n📚 Basic Shelf Endpoints:")
    all_passed = True
    
    if not test_api_endpoint(f"{base_url}/api/shelves", "GET", None, 200):
        all_passed = False
    
    # Test getting specific shelf (using test data shelf)
    if not test_api_endpoint(f"{base_url}/api/shelves/Library/Test Shelf", "GET", None, 200):
        all_passed = False
    
    # Test getting non-existent shelf
    if not test_api_endpoint(f"{base_url}/api/shelves/NonExistent/Fake Shelf", "GET", None, 404):
        all_passed = False
    
    # Test creating a new shelf
    print("\n🔨 Shelf Creation Tests:")
    test_shelf_data = {
        "location": "Test Room",
        "name": "API Test Shelf",
        "rows": 3,
        "columns": 4,
        "description": "Created by API test"
    }
    
    if test_api_endpoint(f"{base_url}/api/shelves", "POST", test_shelf_data, 200):
        print("   📋 Shelf created successfully")
        
        # Verify the shelf was created by retrieving it
        if test_api_endpoint(f"{base_url}/api/shelves/Test Room/API Test Shelf", "GET", None, 200):
            print("   📋 Shelf retrieval confirmed")
        else:
            all_passed = False
            
        # Test creating duplicate shelf (should fail)
        if test_api_endpoint(f"{base_url}/api/shelves", "POST", test_shelf_data, 400):
            print("   📋 Duplicate creation properly rejected")
        else:
            all_passed = False
    else:
        all_passed = False
    
    # Test invalid shelf creation
    print("\n❌ Error Scenario Tests:")
    invalid_shelf_data = {
        "location": "Test Room",
        "name": "Invalid Shelf",
        "rows": 0,  # Invalid - must be positive
        "columns": 5,
        "description": "This should fail"
    }
    
    if test_api_endpoint(f"{base_url}/api/shelves", "POST", invalid_shelf_data, 400):
        print("   📋 Invalid dimensions properly rejected")
    else:
        all_passed = False
    
    # Test deleting the test shelf
    print("\n🗑️  Shelf Deletion Tests:")
    if test_api_endpoint(f"{base_url}/api/shelves/Test Room/API Test Shelf", "DELETE", None, 200):
        print("   📋 Shelf deleted successfully")
        
        # Verify the shelf was deleted
        if test_api_endpoint(f"{base_url}/api/shelves/Test Room/API Test Shelf", "GET", None, 404):
            print("   📋 Shelf deletion confirmed")
        else:
            all_passed = False
    else:
        all_passed = False
    
    # Test deleting non-existent shelf
    if test_api_endpoint(f"{base_url}/api/shelves/NonExistent/Fake Shelf", "DELETE", None, 404):
        print("   📋 Non-existent shelf deletion properly rejected")
    else:
        all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("🎉 All shelf API tests passed!")
        print("✅ Your shelf management API is working correctly with test data")
    else:
        print("⚠️  Some shelf API tests failed. Check the server logs.")
        sys.exit(1)

if __name__ == "__main__":
    print("📋 Make sure you've switched to test data:")
    print("   ./switch_data.sh test")
    print("📋 Make sure the API server is running:")
    print("   python main.py web --reload")
    print()
    input("Press Enter when ready to run shelf API tests...")
    main()