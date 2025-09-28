"""
Book information lookup services using ISBN.
"""

import logging
import os
from typing import Optional, Dict, Any
import isbnlib
import requests
from .models import BookInfo

logger = logging.getLogger(__name__)


class BookLookupService:
    """Service for looking up book information from ISBN."""
    
    def __init__(self) -> None:
        """Initialize the lookup service."""
        self.google_books_base_url: str = "https://www.googleapis.com/books/v1/volumes"
        self.google_books_api_key: Optional[str] = os.getenv('GOOGLE_BOOKS_API_KEY')
    
    def get_book_info(self, isbn: str) -> Optional[BookInfo]:
        """Get book information from ISBN using multiple sources.
        
        Args:
            isbn: ISBN-10 or ISBN-13 string
            
        Returns:
            BookInfo object if found, None otherwise
        """
        # Clean and validate ISBN
        clean_isbn = isbnlib.canonical(isbn)
        if not clean_isbn:
            logger.warning(f"Invalid ISBN: {isbn}")
            return None
        
        # Use Google Books API for more detailed info
        book_info = self._get_from_google_books(clean_isbn)
        if book_info:
            return book_info
        
        # Try isbnlib sources second
        # Unfortunately it doesn't include as much data
        book_info = self._get_from_isbnlib(clean_isbn)
        if book_info:
            return book_info
        
        logger.warning(f"No book information found for ISBN: {isbn}")
        return None
    
    def _get_from_isbnlib(self, isbn: str) -> Optional[BookInfo]:
        """Get book info using isbnlib (tries multiple sources)."""
        try:
            # Try different sources in order of preference
            sources = ['goob', 'openl']  # Google Books, Open Library
            
            for source in sources:
                try:
                    meta = isbnlib.meta(isbn, service=source)
                    if meta:
                        return self._convert_isbnlib_to_bookinfo(isbn, meta)
                except Exception as e:
                    logger.debug(f"Failed to get info from {source}: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"isbnlib lookup failed: {e}")
        
        return None
    
    def _get_from_google_books(self, isbn: str) -> Optional[BookInfo]:
        """Get book info from Google Books API directly."""
        try:
            url = f"{self.google_books_base_url}?q=isbn:{isbn}"
            if self.google_books_api_key:
                url += f"&key={self.google_books_api_key}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if not data.get('items'):
                return None
                
            # Use the first result
            volume_info = data['items'][0].get('volumeInfo', {})
            return self._convert_google_books_to_bookinfo(isbn, volume_info)
            
        except Exception as e:
            logger.debug(f"Google Books API lookup failed: {e}")
            return None
    
    def _convert_isbnlib_to_bookinfo(self, isbn: str, meta: Dict[str, Any]) -> BookInfo:
        """Convert isbnlib metadata to BookInfo object."""
        return BookInfo(
            isbn=isbn,
            title=meta.get('Title', 'Unknown Title'),
            authors=meta.get('Authors', []),
            publisher=meta.get('Publisher'),
            published_date=meta.get('Year'),
            language=meta.get('Language')
        )
    
    def _convert_google_books_to_bookinfo(self, isbn: str, volume_info: Dict[str, Any]) -> BookInfo:
        """Convert Google Books API response to BookInfo object."""
        # Extract cover image URL
        cover_url = None
        if 'imageLinks' in volume_info:
            # Prefer larger images
            for size in ['large', 'medium', 'small', 'thumbnail', 'smallThumbnail']:
                if size in volume_info['imageLinks']:
                    cover_url = volume_info['imageLinks'][size]
                    break
        
        return BookInfo(
            isbn=isbn,
            title=volume_info.get('title', 'Unknown Title'),
            authors=volume_info.get('authors', []),
            publisher=volume_info.get('publisher'),
            published_date=volume_info.get('publishedDate'),
            description=volume_info.get('description'),
            genres=volume_info.get('categories'),
            page_count=volume_info.get('pageCount'),
            cover_url=cover_url,
            language=volume_info.get('language')
        )