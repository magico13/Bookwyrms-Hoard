"""
Simple test script to verify the core functionality works.
"""

from bookwyrms.lookup import BookLookupService

def test_lookup():
    """Test the book lookup functionality."""
    service = BookLookupService()
    
    # Test with a known ISBN
    test_isbn = "9780134685991"  # Effective Java
    print(f"Testing ISBN: {test_isbn}")
    
    book_info = service.get_book_info(test_isbn)
    
    if book_info:
        print("✅ Success!")
        print(f"Title: {book_info.title}")
        print(f"Authors: {book_info.authors}")
        print(f"Description length: {len(book_info.description) if book_info.description else 0} chars")
        return True
    else:
        print("❌ Failed to get book info")
        return False

if __name__ == "__main__":
    test_lookup()