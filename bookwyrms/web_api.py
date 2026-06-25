"""
FastAPI web API for Bookwyrm's Hoard library management.

Thin controller layer — all business logic lives in library_service.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncIterator, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastmcp.utilities.lifespan import combine_lifespans
from pydantic import BaseModel
import uvicorn

from .shelf_models import ShelfLocation, Bookshelf
from .library_service import (
    LibraryError,
    mcp_app,
    storage,
    BookRecordResponse,
    BookshelfResponse,
    book_record_to_response,
    bookshelf_to_response,
    do_checkout_book,
    do_checkin_book,
    do_add_book,
    do_lookup_book,
)

# Import mcp_tools to register MCP tool decorators
from . import mcp_tools  # noqa: F401

logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context for FastAPI app."""
    yield


app = FastAPI(
    title="Bookwyrm's Hoard API",
    description="Personal library management API with barcode scanner support",
    version="1.0.0",
    lifespan=combine_lifespans(app_lifespan, mcp_app.lifespan),
)

# Mount MCP at /mcp
app.mount("/mcp", mcp_app)

# Add CORS middleware to handle preflight OPTIONS requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for the web interface
app.mount("/static", StaticFiles(directory="static"), name="static")


# ------------------------------------------------------------------
# Request models (REST API only)
# ------------------------------------------------------------------
class CheckoutRequest(BaseModel):
    checked_out_to: str


class CheckinRequest(BaseModel):
    location: Optional[str] = None
    bookshelf_name: Optional[str] = None
    column: Optional[int] = None
    row: Optional[int] = None


class CreateBookshelfRequest(BaseModel):
    location: str
    name: str
    rows: int
    columns: int
    description: Optional[str] = None


class AddBookRequest(BaseModel):
    isbn: Optional[str] = None
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    publisher: Optional[str] = None
    published_date: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    bookshelf_name: Optional[str] = None
    column: Optional[int] = None
    row: Optional[int] = None
    notes: Optional[str] = None


# ------------------------------------------------------------------
# REST endpoints — thin wrappers around library_service
# ------------------------------------------------------------------
@app.get("/")
async def root() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/api")
async def api_info() -> Dict[str, str]:
    return {"message": "Bookwyrm's Hoard API", "version": "1.0.0", "docs": "/docs"}


@app.get("/api/books/checked-out")
async def get_checked_out_books() -> List[BookRecordResponse]:
    """Return all books currently checked out of the library. Dates are in UTC ISO-8601 format."""
    try:
        checked_out_books = storage.get_checked_out_books()
        return [book_record_to_response(r) for r in checked_out_books]
    except Exception as e:
        logger.error(f"Error retrieving checked out books: {e}")
        raise HTTPException(status_code=500, detail="Internal server error getting checked out books")


@app.get("/api/books/{isbn}")
async def get_book_by_isbn(isbn: str) -> BookRecordResponse:
    """Get a specific book by ISBN."""
    book_record = storage.get_book(isbn)
    if book_record is None:
        raise HTTPException(status_code=404, detail=f"Book with ISBN {isbn} not found")
    return book_record_to_response(book_record)


@app.get("/api/lookup/{isbn}")
async def lookup_book_by_isbn(isbn: str) -> BookRecordResponse:
    """Look up book information by ISBN from library or external sources."""
    try:
        record = do_lookup_book(isbn)
        return book_record_to_response(record)
    except LibraryError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error looking up book {isbn}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during lookup")


@app.get("/api/books")
async def search_books(
    q: Optional[str] = Query(
        None,
        description="search term for title, author, or ISBN - use plain string like 'Edward Ashton' not with extra quotes",
    )
) -> List[BookRecordResponse]:
    """Search books by query term or get all books if no search criteria provided. Case insensitive."""
    try:
        if q:
            book_records = storage.search_books(q)
            return [book_record_to_response(r) for r in book_records]
        else:
            books = storage.get_books()
            return [book_record_to_response(r) for r in books.values()]
    except Exception as e:
        logger.error(f"Error searching books: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during search")


@app.post("/api/books")
async def add_book(request: AddBookRequest) -> BookRecordResponse:
    """Add a new book to the library, optionally placing it on a specific shelf."""
    try:
        record = do_add_book(
            isbn=request.isbn,
            title=request.title,
            authors=request.authors,
            publisher=request.publisher,
            published_date=request.published_date,
            description=request.description,
            location=request.location,
            bookshelf_name=request.bookshelf_name,
            column=request.column,
            row=request.row,
            notes=request.notes,
        )
        return book_record_to_response(record)
    except LibraryError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error adding book: {e}")
        raise HTTPException(status_code=500, detail="Internal server error adding book")


@app.get("/api/health")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy"}


@app.post("/api/books/{isbn}/checkout")
async def checkout_book(isbn: str, request: CheckoutRequest) -> BookRecordResponse:
    """Check out a book to a person."""
    try:
        record = do_checkout_book(isbn, request.checked_out_to)
        return book_record_to_response(record)
    except LibraryError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error checking out book {isbn}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during checkout")


@app.post("/api/books/{isbn}/checkin")
async def checkin_book(isbn: str, request: Optional[CheckinRequest] = None) -> BookRecordResponse:
    """Check in a book, optionally relocating it to a different shelf."""
    try:
        record = do_checkin_book(
            isbn,
            request.location if request else None,
            request.bookshelf_name if request else None,
            request.column if request else None,
            request.row if request else None,
        )
        return book_record_to_response(record)
    except LibraryError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error checking in book {isbn}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during checkin")


@app.get("/api/shelves")
async def get_all_shelves() -> List[BookshelfResponse]:
    """Get all bookshelves in the library."""
    try:
        bookshelves = storage.get_bookshelves()
        return [bookshelf_to_response(s) for s in bookshelves.values()]
    except Exception as e:
        logger.error(f"Error getting shelves: {e}")
        raise HTTPException(status_code=500, detail="Internal server error getting shelves")


@app.get("/api/shelves/{location}/{name}")
async def get_shelf_by_location_and_name(location: str, name: str) -> BookshelfResponse:
    """Get a specific bookshelf by location and name."""
    bookshelf = storage.get_bookshelf(location, name)
    if bookshelf is None:
        raise HTTPException(
            status_code=404,
            detail=f"Bookshelf '{name}' not found in location '{location}'",
        )
    return bookshelf_to_response(bookshelf)


@app.post("/api/shelves")
async def create_shelf(request: CreateBookshelfRequest) -> BookshelfResponse:
    """Create a new bookshelf."""
    try:
        bookshelf = Bookshelf(
            location=request.location,
            name=request.name,
            rows=request.rows,
            columns=request.columns,
            description=request.description,
        )
        storage.add_bookshelf(bookshelf)
        return bookshelf_to_response(bookshelf)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating shelf: {e}")
        raise HTTPException(status_code=500, detail="Internal server error creating shelf")


@app.delete("/api/shelves/{location}/{name}")
async def delete_shelf(location: str, name: str) -> Dict[str, str]:
    """Delete a bookshelf."""
    try:
        if not storage.get_bookshelf(location, name):
            raise HTTPException(
                status_code=404,
                detail=f"Bookshelf '{name}' not found in location '{location}'",
            )
        success = storage.remove_bookshelf(location, name)
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Bookshelf '{name}' not found in location '{location}'",
            )
        return {"message": f"Successfully deleted bookshelf '{name}' in '{location}'"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting shelf {location}/{name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error deleting shelf")


def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False) -> None:
    """Run the FastAPI server."""
    uvicorn.run(
        "bookwyrms.web_api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    run_server(reload=True)