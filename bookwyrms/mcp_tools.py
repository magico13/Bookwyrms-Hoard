"""
MCP tool definitions for Bookwyrm's Hoard library management.

Thin controller layer — all business logic lives in library_service.
"""

import logging
from typing import List, Optional, Union

from fastapi import HTTPException

from .library_service import (
    LibraryError,
    mcp,
    storage,
    BookRecordResponse,
    BookshelfResponse,
    book_record_to_response,
    bookshelf_to_response,
    do_checkout_book,
    do_checkin_book,
    do_add_book,
    do_lookup_book,
    do_remove_book,
)

# MCP clients may send ISBNs as numbers (e.g. 9780134685991) — coerce to str.
def _to_str(value: Optional[Union[str, int]]) -> Optional[str]:
    if value is None:
        return None
    return str(value)

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# MCP tool definitions — thin wrappers around library_service
# ------------------------------------------------------------------
@mcp.tool
def list_checked_out_books() -> List[BookRecordResponse]:
    """Return all books currently checked out of the library. Dates are in UTC ISO-8601 format."""
    checked_out_books = storage.get_checked_out_books()
    return [book_record_to_response(r) for r in checked_out_books]


@mcp.tool
def search_books(q: Optional[str] = None) -> List[BookRecordResponse]:
    """Search books by query term or get all books if no search criteria provided. Case insensitive. Fields are ANDed together if multiple terms provided, not ORed.

    Args:
        q: Search term that searches title, author, and isbn. If None or empty, returns all books.
    """
    if q:
        book_records = storage.search_books(q)
        return [book_record_to_response(r) for r in book_records]
    else:
        books = storage.get_books()
        return [book_record_to_response(r) for r in books.values()]


@mcp.tool
def list_shelves() -> List[BookshelfResponse]:
    """Get all bookshelves in the library.

    Each bookshelf is a physical multi-shelf grid structure with rows and columns,
    where each shelf holds any number of books. There is NOT one book per row/column position.
    For example, a bookshelf with rows=5 and columns=4 has 20 individual shelves
    arranged in a 5x4 grid. Each shelf is addressed by (column, row) coordinates
    that are 0-indexed from the top-left corner.
    """
    bookshelves = storage.get_bookshelves()
    return [bookshelf_to_response(s) for s in bookshelves.values()]


@mcp.tool
def checkout_book(isbn: Union[str, int], checked_out_to: str, notes: Optional[str] = None) -> BookRecordResponse:
    """Check out a book to a person.

    Args:
        isbn: The ISBN of the book to check out (string or number).
        checked_out_to: Name of the person checking out the book.
        notes: Optional notes about the checkout.

    Returns:
        Updated BookRecord with checkout information.

    Raises:
        HTTPException: 404 if book not found, 400 if already checked out.
    """
    try:
        isbn_str = _to_str(isbn)
        assert isbn_str is not None
        record = do_checkout_book(isbn_str, checked_out_to, notes)
        return book_record_to_response(record)
    except LibraryError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error checking out book {isbn}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during checkout")


@mcp.tool
def checkin_book(
    isbn: Union[str, int],
    location: Optional[str] = None,
    bookshelf_name: Optional[str] = None,
    column: Optional[int] = None,
    row: Optional[int] = None,
) -> BookRecordResponse:
    """Check in a book, optionally placing it on a specific shelf.

    Args:
        isbn: The ISBN of the book to check in (string or number).
        location: Physical location like 'Library' or 'Office'. Required if relocating.
        bookshelf_name: Name of the bookshelf structure. Required if relocating.
        column: Column coordinate (0-indexed). Required if relocating.
        row: Row coordinate (0-indexed). Required if relocating.

    Returns:
        Updated BookRecord with check-in information.

    Raises:
        HTTPException: 404 if book not found, 400 if not checked out or invalid shelf coordinates.
    """
    try:
        isbn_str = _to_str(isbn)
        assert isbn_str is not None
        record = do_checkin_book(isbn_str, location, bookshelf_name, column, row)
        return book_record_to_response(record)
    except LibraryError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error checking in book {isbn}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during check-in")


@mcp.tool
def add_book(
    isbn: Optional[Union[str, int]] = None,
    title: Optional[str] = None,
    authors: Optional[List[str]] = None,
    publisher: Optional[str] = None,
    published_date: Optional[Union[str, int]] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    bookshelf_name: Optional[str] = None,
    column: Optional[int] = None,
    row: Optional[int] = None,
    notes: Optional[str] = None,
) -> BookRecordResponse:
    """Add a new book to the library, optionally placing it on a specific shelf.

    Supports two modes:
    1. ISBN lookup: Provide an ISBN and the system will look up book details automatically.
    2. Manual entry: Provide a title (and optionally authors, publisher, etc.) to add a book manually.

    Args:
        isbn: ISBN for automatic lookup (string or number). If lookup fails, falls back to manual entry.
        title: Book title (required for manual entry).
        authors: List of author names.
        publisher: Publisher name.
        published_date: Publication date (string or number, e.g. "2026" or 2026).
        description: Book description.
        location: Physical location like 'Library' or 'Office'. Required if placing on a shelf.
        bookshelf_name: Name of the bookshelf structure. Required if placing on a shelf.
        column: Column coordinate (0-indexed). Required if placing on a shelf.
        row: Row coordinate (0-indexed). Required if placing on a shelf.
        notes: Optional notes about the book.

    Returns:
        Created BookRecord.

    Raises:
        HTTPException: 400 if invalid parameters or book already exists.
    """
    try:
        record = do_add_book(
            isbn=_to_str(isbn),
            title=title,
            authors=authors,
            publisher=publisher,
            published_date=_to_str(published_date),
            description=description,
            location=location,
            bookshelf_name=bookshelf_name,
            column=column,
            row=row,
            notes=notes,
        )
        return book_record_to_response(record)
    except LibraryError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error adding book: {e}")
        raise HTTPException(status_code=500, detail="Internal server error adding book")


@mcp.tool
def lookup_book(isbn: Union[str, int]) -> BookRecordResponse:
    """Look up a book by ISBN from the library or external sources.

    If the book exists in the library, returns the complete record with location
    and checkout status. If not in the library, performs an external lookup
    (via isbnlib/Google Books) and returns basic book information with
    home_location=None.

    Args:
        isbn: The ISBN of the book to look up (string or number).

    Returns:
        BookRecord with book details. home_location will be None if the book
        is not in the library.

    Raises:
        HTTPException: 404 if book not found anywhere.
    """
    try:
        isbn_str = _to_str(isbn)
        assert isbn_str is not None
        record = do_lookup_book(isbn_str)
        return book_record_to_response(record)
    except LibraryError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error looking up book {isbn}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during lookup")

@mcp.tool
def remove_book(isbn: Union[str, int]) -> BookRecordResponse:
    """Permanently remove a book from the library by ISBN. This is a destructive operation and should be used with caution.

    Args:
        isbn: The ISBN of the book to remove (string or number).

    Returns:
        BookRecordResponse of the removed book.

    Raises:
        HTTPException: 404 if the book is not found.
    """
    try:
        isbn_str = _to_str(isbn)
        assert isbn_str is not None
        # get the book record to check if it exists before attempting removal
        record = storage.get_book(isbn_str)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Book with ISBN '{isbn_str}' not found")
        success = do_remove_book(isbn_str)
        if not success:
            raise HTTPException(status_code=404, detail=f"Book with ISBN '{isbn}' not found")
        return book_record_to_response(record)
    except LibraryError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error removing book {isbn}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error removing book")
