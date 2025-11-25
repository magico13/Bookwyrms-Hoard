"""
FastAPI web API for Bookwyrm's Hoard library management.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mcp import FastApiMCP
from pydantic import BaseModel
import uvicorn

from .storage import BookshelfStorage
from .shelf_models import ShelfLocation, Bookshelf, BookRecord
from .lookup import BookLookupService
from .models import BookInfo
from .time_utils import to_utc_iso

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Bookwyrm's Hoard API",
    description="Personal library management API with barcode scanner support",
    version="1.0.0"
)

# Add CORS middleware to handle preflight OPTIONS requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for MCP server usage
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods including OPTIONS
    allow_headers=["*"],  # Allow all headers
)

# Initialize storage and lookup service - these will be shared across all requests
storage = BookshelfStorage()
lookup_service = BookLookupService()

# Mount static files for the web interface
app.mount("/static", StaticFiles(directory="static"), name="static")

# MCP server support
mcp = FastApiMCP(
    app,
    include_tags=["mcp"],
    name="Bookwyrm's Hoard MCP",
    description="MCP server for Bookwyrm's Hoard library management. Each bookshelf is a multi-shelf grid structure with rows and columns (e.g., a 5x4 bookshelf has 20 individual shelves arranged in a grid). Each shelf in the grid can hold multiple books and is identified by (column, row) coordinates that are 0-indexed from top-left.",
    describe_full_response_schema=True
)
# Mount the MCP server directly to your FastAPI app
mcp.mount()

# Request/Response models
class CheckoutRequest(BaseModel):
    """Request model for checking out a book."""
    checked_out_to: str


class CheckinRequest(BaseModel):
    """Request model for checking in a book, optionally to a new shelf on a bookshelf structure."""
    location: Optional[str] = None  # Physical location like 'Library' or 'Office'
    bookshelf_name: Optional[str] = None  # Name of the specific bookshelf structure in that location
    column: Optional[int] = None  # Column coordinate (0-indexed from left) of the individual shelf
    row: Optional[int] = None  # Row coordinate (0-indexed from top) of the individual shelf


class CreateBookshelfRequest(BaseModel):
    """Request model for creating a new bookshelf structure with multiple shelves arranged in a grid."""
    location: str  # Physical location like 'Library' or 'Office'
    name: str  # Name of the bookshelf structure (e.g., 'Large bookshelf')
    rows: int  # Number of rows of shelves in the grid (creates rows * columns total shelves)
    columns: int  # Number of columns of shelves in the grid
    description: Optional[str] = None


class AddBookRequest(BaseModel):
    """Request model for adding a new book to the library."""
    isbn: Optional[str] = None  # For ISBN lookup
    # Manual entry fields (used if ISBN lookup fails or ISBN not provided)
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    publisher: Optional[str] = None
    published_date: Optional[str] = None
    description: Optional[str] = None
    # Optional shelf location (all 4 fields required if specifying a shelf)
    location: Optional[str] = None  # Physical location like 'Library' or 'Office'
    bookshelf_name: Optional[str] = None  # Name of the specific bookshelf structure
    column: Optional[int] = None  # Column coordinate (0-indexed from left) of the individual shelf
    row: Optional[int] = None  # Row coordinate (0-indexed from top) of the individual shelf
    # Optional notes
    notes: Optional[str] = None


# Response models for MCP server schema generation
class ShelfLocationResponse(BaseModel):
    """Response model for shelf location information."""
    location: str  # Physical location like 'Library' or 'Office'
    bookshelf_name: str  # Name of the bookshelf structure
    column: int  # Column coordinate (0-indexed from left) of the individual shelf
    row: int  # Row coordinate (0-indexed from top) of the individual shelf


class BookInfoResponse(BaseModel):
    """Response model for book information."""
    isbn: str
    title: str
    authors: List[str]
    publisher: Optional[str] = None
    published_date: Optional[str] = None
    description: Optional[str] = None
    genres: Optional[List[str]] = None
    page_count: Optional[int] = None
    cover_url: Optional[str] = None
    language: Optional[str] = None


class BookRecordResponse(BaseModel):
    """Response model for complete book record with location and checkout info."""
    book_info: BookInfoResponse
    home_location: Optional[ShelfLocationResponse] = None
    checked_out_to: Optional[str] = None
    checked_out_date: Optional[str] = None
    notes: Optional[str] = None


class BookshelfResponse(BaseModel):
    """Response model for bookshelf structure information."""
    location: str  # Physical location like 'Library' or 'Office'
    name: str  # Name of the bookshelf structure
    rows: int  # Number of rows of shelves in the grid
    columns: int  # Number of columns of shelves in the grid
    description: Optional[str] = None


# Helper functions to convert domain objects to response models
def _shelf_location_to_response(location: ShelfLocation) -> ShelfLocationResponse:
    """Convert ShelfLocation to response model."""
    return ShelfLocationResponse(
        location=location.location,
        bookshelf_name=location.bookshelf_name,
        column=location.column,
        row=location.row
    )


def _book_info_to_response(book_info: BookInfo) -> BookInfoResponse:
    """Convert BookInfo to response model."""
    return BookInfoResponse(
        isbn=book_info.isbn,
        title=book_info.title,
        authors=book_info.authors,
        publisher=book_info.publisher,
        published_date=book_info.published_date,
        description=book_info.description,
        genres=book_info.genres,
        page_count=book_info.page_count,
        cover_url=book_info.cover_url,
        language=book_info.language
    )


def _book_record_to_response(record: BookRecord) -> BookRecordResponse:
    """Convert BookRecord to response model."""
    return BookRecordResponse(
        book_info=_book_info_to_response(record.book_info),
        home_location=_shelf_location_to_response(record.home_location) if record.home_location else None,
        checked_out_to=record.checked_out_to,
        checked_out_date=record.checked_out_date,
        notes=record.notes
    )


def _bookshelf_to_response(bookshelf: Bookshelf) -> BookshelfResponse:
    """Convert Bookshelf to response model."""
    return BookshelfResponse(
        location=bookshelf.location,
        name=bookshelf.name,
        rows=bookshelf.rows,
        columns=bookshelf.columns,
        description=bookshelf.description
    )


@app.get("/")
async def root() -> FileResponse:
    """Serve the main kiosk interface."""
    return FileResponse('static/index.html')


@app.get("/api")
async def api_info() -> Dict[str, str]:
    """API information endpoint."""
    return {
        "message": "Bookwyrm's Hoard API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/api/books/checked-out", tags=["mcp"], operation_id="list_checked_out_books")
async def get_checked_out_books() -> List[BookRecordResponse]:
    """Return all books currently checked out of the library."""
    try:
        checked_out_books = storage.get_checked_out_books()
        return [_book_record_to_response(book_record) for book_record in checked_out_books]
    except Exception as e:
        logger.error(f"Error retrieving checked out books: {e}")
        raise HTTPException(status_code=500, detail="Internal server error getting checked out books")


@app.get("/api/books/{isbn}")
async def get_book_by_isbn(isbn: str) -> BookRecordResponse:
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
    
    return _book_record_to_response(book_record)


@app.get("/api/lookup/{isbn}")
async def lookup_book_by_isbn(isbn: str) -> BookRecordResponse:
    """
    Look up book information by ISBN from library or external sources.
    
    Returns book information in BookRecord format. If the book exists in the library,
    returns the complete record with location and checkout status. If the book is not
    in the library, performs external lookup and returns BookRecord format with
    home_location=null.
    
    Args:
        isbn: The ISBN of the book to look up
        
    Returns:
        BookRecord as JSON dictionary (with home_location=null if not in library)
        
    Raises:
        HTTPException: 404 if book not found anywhere
    """
    try:
        # First check if we have it in our library
        book_record = storage.get_book(isbn)
        if book_record is not None:
            return _book_record_to_response(book_record)
        
        # Not in library, try external lookup
        book_info = lookup_service.get_book_info(isbn)
        if book_info is None:
            raise HTTPException(status_code=404, detail=f"Book with ISBN {isbn} not found")
        
        # Create a BookRecord-like response with null location fields
        book_record = BookRecord(
            book_info=book_info,
            home_location=None,
            checked_out_to=None,
            checked_out_date=None,
            notes=None
        )
        
        return _book_record_to_response(book_record)
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error looking up book {isbn}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during lookup")


@app.get("/api/books", tags=["mcp"], operation_id="search_books")
async def search_books(
    q: Optional[str] = Query(None, description="search term for title, author, or ISBN - use plain string like 'Edward Ashton' not with extra quotes")
) -> List[BookRecordResponse]:
    """
    Search books by query term or get all books if no search criteria provided. Case insensitive.
    Fields are ANDed together if multiple terms provided, not ORed.
    
    For MCP clients: When calling this endpoint, pass the query parameter as a simple string value.
    For author names with spaces like "Edward Ashton", use: {"q": "Edward Ashton"}
    NOT: {"q": "\"Edward Ashton\""} or {\"q\":\"Edward Ashton\"}
    
    Args:
        q: Smart search term that searches title, author, and isbn
        
    Returns:
        List of BookRecord objects as JSON dictionaries
        If no search parameters provided, returns all books in the library
    """
    try:
        if q:
            # Smart unified search
            book_records = storage.search_books(q)
            return [_book_record_to_response(book_record) for book_record in book_records]
        else:
            # No search criteria - return all books
            books = storage.get_books()
            return [_book_record_to_response(book_record) for book_record in books.values()]
    except Exception as e:
        logger.error(f"Error searching books: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during search")


@app.post("/api/books")
async def add_book(request: AddBookRequest) -> BookRecordResponse:
    """
    Add a new book to the library, optionally placing it on a specific shelf.
    
    Args:
        request: Add book request with ISBN (for lookup) or manual book details,
                plus optional shelf location (location, bookshelf_name, column, row)
                
    Returns:
        Created BookRecord as JSON dictionary
        
    Raises:
        HTTPException: 400 if invalid parameters, book already exists, or shelf coordinates are invalid
    """
    try:
        book_info: Optional[BookInfo] = None
        
        # Try ISBN lookup first if provided
        if request.isbn:
            book_info = lookup_service.get_book_info(request.isbn)
            if not book_info:
                # ISBN lookup failed, but we can try manual entry
                if not request.title:
                    raise HTTPException(
                        status_code=400,
                        detail=f"ISBN {request.isbn} not found and no manual title provided"
                    )
        
        # Use manual entry if no ISBN or ISBN lookup failed
        if not book_info:
            if not request.title:
                raise HTTPException(
                    status_code=400,
                    detail="Either ISBN or title must be provided"
                )
            
            # Generate fake ISBN if none provided
            isbn_to_use = request.isbn
            if not isbn_to_use:
                import uuid
                fake_id = str(uuid.uuid4()).replace('-', '')[:10]
                isbn_to_use = f"FAKE{fake_id}"
            
            book_info = BookInfo(
                isbn=isbn_to_use,
                title=request.title,
                authors=request.authors or ["Unknown Author"],
                publisher=request.publisher,
                published_date=request.published_date,
                description=request.description
            )
        
        # Check if book already exists
        existing_book = storage.get_book(book_info.isbn)
        if existing_book:
            raise HTTPException(
                status_code=400,
                detail=f"Book with ISBN {book_info.isbn} already exists in library"
            )
        
        # Handle optional shelf location
        shelf_location: Optional[ShelfLocation] = None
        if all([request.location, request.bookshelf_name, 
                request.column is not None, request.row is not None]):
            
            # Type assertions - we know these are not None after validation above
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
            
            # Validate shelf coordinates are within bookshelf bounds
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
            
            shelf_location = ShelfLocation(
                location=location,
                bookshelf_name=bookshelf_name,
                column=column,
                row=row
            )
        
        # Create book record
        book_record = BookRecord(
            book_info=book_info,
            home_location=shelf_location,
            notes=request.notes
        )
        
        # Save to storage
        storage.add_or_update_book(book_record)
        
        return _book_record_to_response(book_record)
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error adding book: {e}")
        raise HTTPException(status_code=500, detail="Internal server error adding book")


@app.get("/api/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/books/{isbn}/checkout")
async def checkout_book(isbn: str, request: CheckoutRequest) -> BookRecordResponse:
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
        book_record.checked_out_date = to_utc_iso(datetime.now())
        
        # Save the updated record
        storage.add_or_update_book(book_record)
        
        return _book_record_to_response(book_record)
    except Exception as e:
        logger.error(f"Error checking out book {isbn}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during checkout")


@app.post("/api/books/{isbn}/checkin")
async def checkin_book(isbn: str, request: Optional[CheckinRequest] = None) -> BookRecordResponse:
    """
    Check in a book, optionally relocating it to a different shelf.
    
    Args:
        isbn: The ISBN of the book to check in
        request: Optional check-in request with new shelf location details
        
    Returns:
        Updated BookRecord as JSON dictionary
        
    Raises:
        HTTPException: 404 if book not found, 400 if not checked out or invalid shelf coordinates
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
            
            # Validate shelf coordinates are within bookshelf bounds
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
        
        return _book_record_to_response(book_record)
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error checking in book {isbn}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during checkin")


@app.get("/api/shelves", tags=["mcp"], operation_id="list_shelves")
async def get_all_shelves() -> List[BookshelfResponse]:
    """
    Get all bookshelves in the library.
    
    Each bookshelf is a physical multi-shelf grid structure with rows and columns,
    where each shelf holds any number of books. There is NOT one book per row/column position.
    For example, a bookshelf with rows=5 and columns=4 has 20 individual shelves
    arranged in a 5x4 grid. Each shelf is addressed
    by (column, row) coordinates that are 0-indexed from the top-left corner.
    
    Returns:
        List of Bookshelf objects as JSON dictionaries, each showing the grid dimensions
        of individual shelves within the bookshelf structure
    """
    try:
        bookshelves = storage.get_bookshelves()
        return [_bookshelf_to_response(bookshelf) for bookshelf in bookshelves.values()]
    except Exception as e:
        logger.error(f"Error getting shelves: {e}")
        raise HTTPException(status_code=500, detail="Internal server error getting shelves")


@app.get("/api/shelves/{location}/{name}")
async def get_shelf_by_location_and_name(location: str, name: str) -> BookshelfResponse:
    """
    Get a specific bookshelf by location and name.
    
    Returns the bookshelf grid structure showing its dimensions (rows x columns).
    Each position in the grid is an individual shelf that can hold multiple books at coordinates (column, row).
    
    Args:
        location: The location where the bookshelf is located (e.g., 'Library')
        name: The name of the bookshelf (e.g., 'Large bookshelf')
        
    Returns:
        Bookshelf as JSON dictionary showing the grid dimensions of individual shelves
        
    Raises:
        HTTPException: 404 if bookshelf not found
    """
    bookshelf = storage.get_bookshelf(location, name)
    if bookshelf is None:
        raise HTTPException(
            status_code=404, 
            detail=f"Bookshelf '{name}' not found in location '{location}'"
        )
    
    return _bookshelf_to_response(bookshelf)


@app.post("/api/shelves")
async def create_shelf(request: CreateBookshelfRequest) -> BookshelfResponse:
    """
    Create a new bookshelf.
    
    Args:
        request: Create bookshelf request with location, name, dimensions, and optional description
        
    Returns:
        Created Bookshelf as JSON dictionary
        
    Raises:
        HTTPException: 400 if bookshelf already exists or invalid parameters
    """
    try:
        # Create bookshelf object - this will validate dimensions
        bookshelf = Bookshelf(
            location=request.location,
            name=request.name,
            rows=request.rows,
            columns=request.columns,
            description=request.description
        )
        
        # Add to storage
        storage.add_bookshelf(bookshelf)
        
        return _bookshelf_to_response(bookshelf)
    except ValueError as e:
        # Handle validation errors (e.g., dimensions, duplicate shelf)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating shelf: {e}")
        raise HTTPException(status_code=500, detail="Internal server error creating shelf")


@app.delete("/api/shelves/{location}/{name}")
async def delete_shelf(location: str, name: str) -> Dict[str, str]:
    """
    Delete a bookshelf.
    
    Args:
        location: The location where the bookshelf is located
        name: The name of the bookshelf to delete
        
    Returns:
        Success message
        
    Raises:
        HTTPException: 404 if bookshelf not found, 400 if shelf has books assigned
    """
    try:
        # Check if bookshelf exists
        if not storage.get_bookshelf(location, name):
            raise HTTPException(
                status_code=404,
                detail=f"Bookshelf '{name}' not found in location '{location}'"
            )
        
        # Attempt to remove the bookshelf
        success = storage.remove_bookshelf(location, name)
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Bookshelf '{name}' not found in location '{location}'"
            )
        
        return {"message": f"Successfully deleted bookshelf '{name}' in '{location}'"}
    except ValueError as e:
        # Handle case where shelf has books assigned
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error deleting shelf {location}/{name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error deleting shelf")

mcp.setup_server()

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