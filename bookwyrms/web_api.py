"""
FastAPI web API for Bookwyrms-Hoard library management.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import uvicorn

from .storage import BookshelfStorage
from .shelf_models import ShelfLocation

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Bookwyrms-Hoard API",
    description="Personal library management API with barcode scanner support",
    version="1.0.0"
)

# Initialize storage - this will be shared across all requests
storage = BookshelfStorage()


# Request/Response models
class CheckoutRequest(BaseModel):
    """Request model for checking out a book."""
    checked_out_to: str


class CheckinRequest(BaseModel):
    """Request model for checking in a book, optionally to a new location."""
    location: Optional[str] = None
    bookshelf_name: Optional[str] = None
    column: Optional[int] = None
    row: Optional[int] = None


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint with API information."""
    return {
        "message": "Bookwyrms-Hoard API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/api/books/{isbn}")
async def get_book_by_isbn(isbn: str) -> Dict[str, Any]:
    """
    Get a specific book by ISBN.
    
    Args:
        isbn: The ISBN of the book to retrieve
        
    Returns:
        BookRecord as JSON dictionary
        
    Raises:
        HTTPException: 404 if book not found
    """
    book_record = storage.get_book(isbn)
    if book_record is None:
        raise HTTPException(status_code=404, detail=f"Book with ISBN {isbn} not found")
    
    return book_record.to_dict()


@app.get("/api/books")
async def search_books(
    title: Optional[str] = Query(None, description="Search term for book title"),
    author: Optional[str] = Query(None, description="Search term for author name")
) -> List[Dict[str, Any]]:
    """
    Search books by title and/or author, or get all books if no search criteria provided.
    
    Args:
        title: Optional search term for book title (case-insensitive contains)
        author: Optional search term for author name (case-insensitive contains)
        
    Returns:
        List of BookRecord objects as JSON dictionaries
        If no search parameters provided, returns all books in the library
    """
    try:
        if not title and not author:
            # No search criteria - return all books
            books = storage.get_books()
            return [book_record.to_dict() for book_record in books.values()]
        else:
            # Search with provided criteria
            book_records = storage.search_books(title=title, author=author)
            return [book_record.to_dict() for book_record in book_records]
    except Exception as e:
        logger.error(f"Error searching books: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during search")


@app.get("/api/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/books/{isbn}/checkout")
async def checkout_book(isbn: str, request: CheckoutRequest) -> Dict[str, Any]:
    """
    Check out a book to a person.
    
    Args:
        isbn: The ISBN of the book to check out
        request: Checkout request with person's name
        
    Returns:
        Updated BookRecord as JSON dictionary
        
    Raises:
        HTTPException: 404 if book not found, 400 if already checked out
    """
    book_record = storage.get_book(isbn)
    if book_record is None:
        raise HTTPException(status_code=404, detail=f"Book with ISBN {isbn} not found")
    
    if book_record.is_checked_out:
        raise HTTPException(
            status_code=400, 
            detail=f"Book is already checked out to {book_record.checked_out_to}"
        )
    
    try:
        # Update checkout information
        book_record.checked_out_to = request.checked_out_to
        book_record.checked_out_date = datetime.now().isoformat()
        
        # Save the updated record
        storage.add_or_update_book(book_record)
        
        return book_record.to_dict()
    except Exception as e:
        logger.error(f"Error checking out book {isbn}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during checkout")


@app.post("/api/books/{isbn}/checkin")
async def checkin_book(isbn: str, request: Optional[CheckinRequest] = None) -> Dict[str, Any]:
    """
    Check in a book, optionally relocating it to a new shelf position.
    
    Args:
        isbn: The ISBN of the book to check in
        request: Optional check-in request with new location details
        
    Returns:
        Updated BookRecord as JSON dictionary
        
    Raises:
        HTTPException: 404 if book not found, 400 if not checked out or invalid location
    """
    book_record = storage.get_book(isbn)
    if book_record is None:
        raise HTTPException(status_code=404, detail=f"Book with ISBN {isbn} not found")
    
    if not book_record.is_checked_out:
        raise HTTPException(status_code=400, detail="Book is not currently checked out")
    
    try:
        # Clear checkout information
        book_record.checked_out_to = None
        book_record.checked_out_date = None
        
        # Handle optional relocation
        if request and any([request.location, request.bookshelf_name, request.column, request.row]):
            # Validate that all location fields are provided
            if not all([request.location, request.bookshelf_name, 
                       request.column is not None, request.row is not None]):
                raise HTTPException(
                    status_code=400,
                    detail="If relocating, all location fields (location, bookshelf_name, column, row) must be provided"
                )
            
            # Type assertion - we know these are not None after validation above
            location = request.location
            bookshelf_name = request.bookshelf_name
            column = request.column
            row = request.row
            assert location is not None and bookshelf_name is not None
            assert column is not None and row is not None
            
            # Validate that the bookshelf exists and position is valid
            bookshelf = storage.get_bookshelf(location, bookshelf_name)
            if bookshelf is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Bookshelf '{bookshelf_name}' not found in location '{location}'"
                )
            
            # Validate position is within bookshelf bounds
            if not (0 <= column < bookshelf.columns):
                raise HTTPException(
                    status_code=400,
                    detail=f"Column {column} is out of bounds for bookshelf (0-{bookshelf.columns - 1})"
                )
            
            if not (0 <= row < bookshelf.rows):
                raise HTTPException(
                    status_code=400,
                    detail=f"Row {row} is out of bounds for bookshelf (0-{bookshelf.rows - 1})"
                )
            
            # Update the home location
            book_record.home_location = ShelfLocation(
                location=location,
                bookshelf_name=bookshelf_name,
                column=column,
                row=row
            )
        
        # Save the updated record
        storage.add_or_update_book(book_record)
        
        return book_record.to_dict()
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error checking in book {isbn}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during checkin")


def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False) -> None:
    """
    Run the FastAPI server.
    
    Args:
        host: Host to bind to (default: 0.0.0.0 for Docker)
        port: Port to bind to (default: 8000)
        reload: Enable auto-reload for development (default: False)
    """
    uvicorn.run(
        "bookwyrms.web_api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    # For development - run with reload
    run_server(reload=True)