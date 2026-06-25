"""
Shared business logic for Bookwyrm's Hoard library management.

This module sits between the REST API (web_api.py) and MCP tools (mcp_tools.py).
Both controllers import from here — no cross-controller dependencies.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastmcp import FastMCP
from pydantic import BaseModel

from .storage import BookshelfStorage
from .shelf_models import ShelfLocation, Bookshelf, BookRecord
from .lookup import BookLookupService
from .models import BookInfo
from .time_utils import to_utc_iso

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Infrastructure
# ------------------------------------------------------------------
storage = BookshelfStorage()
lookup_service = BookLookupService()

# MCP server (exported so mcp_tools can register tools)
mcp = FastMCP("Bookwyrm's Hoard MCP")
mcp_app = mcp.http_app(path="/")

# ------------------------------------------------------------------
# Pydantic response models (shared by both controllers)
# ------------------------------------------------------------------
class ShelfLocationResponse(BaseModel):
    location: str
    bookshelf_name: str
    column: int
    row: int


class BookInfoResponse(BaseModel):
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
    book_info: BookInfoResponse
    home_location: Optional[ShelfLocationResponse] = None
    checked_out_to: Optional[str] = None
    checked_out_date: Optional[str] = None
    notes: Optional[str] = None


class BookshelfResponse(BaseModel):
    location: str
    name: str
    rows: int
    columns: int
    description: Optional[str] = None


# ------------------------------------------------------------------
# Converters (domain objects → Pydantic responses)
# ------------------------------------------------------------------
def shelf_location_to_response(location: ShelfLocation) -> ShelfLocationResponse:
    return ShelfLocationResponse(
        location=location.location,
        bookshelf_name=location.bookshelf_name,
        column=location.column,
        row=location.row,
    )


def book_info_to_response(book_info: BookInfo) -> BookInfoResponse:
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
        language=book_info.language,
    )


def book_record_to_response(record: BookRecord) -> BookRecordResponse:
    return BookRecordResponse(
        book_info=book_info_to_response(record.book_info),
        home_location=shelf_location_to_response(record.home_location)
        if record.home_location
        else None,
        checked_out_to=record.checked_out_to,
        checked_out_date=record.checked_out_date,
        notes=record.notes,
    )


def bookshelf_to_response(bookshelf: Bookshelf) -> BookshelfResponse:
    return BookshelfResponse(
        location=bookshelf.location,
        name=bookshelf.name,
        rows=bookshelf.rows,
        columns=bookshelf.columns,
        description=bookshelf.description,
    )


# ------------------------------------------------------------------
# Custom exception for business logic errors
# ------------------------------------------------------------------
class LibraryError(Exception):
    """Raised when a business rule is violated."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# ------------------------------------------------------------------
# Shelf location validation helper
# ------------------------------------------------------------------
def _validate_shelf_location(
    location: Optional[str],
    bookshelf_name: Optional[str],
    column: Optional[int],
    row: Optional[int],
) -> Optional[ShelfLocation]:
    """Validate and return a ShelfLocation, or None if no location was given."""
    if not all([location, bookshelf_name, column is not None, row is not None]):
        return None  # Partial location is treated as "no location"

    # Type narrowing — all values are non-None after the guard above
    assert location is not None
    assert bookshelf_name is not None
    assert column is not None
    assert row is not None

    bookshelf = storage.get_bookshelf(location, bookshelf_name)
    if bookshelf is None:
        raise LibraryError(
            f"Bookshelf '{bookshelf_name}' not found in location '{location}'",
            status_code=400,
        )

    if not (0 <= column < bookshelf.columns):
        raise LibraryError(
            f"Column {column} is out of bounds for bookshelf (0-{bookshelf.columns - 1})",
            status_code=400,
        )

    if not (0 <= row < bookshelf.rows):
        raise LibraryError(
            f"Row {row} is out of bounds for bookshelf (0-{bookshelf.rows - 1})",
            status_code=400,
        )

    return bookshelf.get_shelf_location(column, row)


# ------------------------------------------------------------------
# Business logic methods
# ------------------------------------------------------------------
def do_checkout_book(
    isbn: str, checked_out_to: str, notes: Optional[str] = None
) -> BookRecord:
    """Check out a book to a person. Returns the updated BookRecord."""
    book_record = storage.get_book(isbn)
    if book_record is None:
        raise LibraryError(f"Book with ISBN {isbn} not found", status_code=404)

    if book_record.is_checked_out:
        raise LibraryError(
            f"Book is already checked out to {book_record.checked_out_to}",
            status_code=400,
        )

    book_record.checked_out_to = checked_out_to
    book_record.checked_out_date = to_utc_iso(datetime.now())
    if notes is not None:
        book_record.notes = notes

    storage.add_or_update_book(book_record)
    return book_record


def do_checkin_book(
    isbn: str,
    location: Optional[str] = None,
    bookshelf_name: Optional[str] = None,
    column: Optional[int] = None,
    row: Optional[int] = None,
) -> BookRecord:
    """Check in a book, optionally placing it on a specific shelf."""
    book_record = storage.get_book(isbn)
    if book_record is None:
        raise LibraryError(f"Book with ISBN {isbn} not found", status_code=404)

    if not book_record.is_checked_out:
        raise LibraryError("Book is not currently checked out", status_code=400)

    book_record.checked_out_to = None
    book_record.checked_out_date = None

    if any([location, bookshelf_name, column is not None, row is not None]):
        if not all([location, bookshelf_name, column is not None, row is not None]):
            raise LibraryError(
                "If relocating, all location fields (location, bookshelf_name, column, row) must be provided",
                status_code=400,
            )
        book_record.home_location = _validate_shelf_location(
            location, bookshelf_name, column, row
        )

    storage.add_or_update_book(book_record)
    return book_record


def do_add_book(
    isbn: Optional[str] = None,
    title: Optional[str] = None,
    authors: Optional[List[str]] = None,
    publisher: Optional[str] = None,
    published_date: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    bookshelf_name: Optional[str] = None,
    column: Optional[int] = None,
    row: Optional[int] = None,
    notes: Optional[str] = None,
) -> BookRecord:
    """Add a new book to the library, optionally placing it on a shelf."""
    book_info: Optional[BookInfo] = None

    # Try ISBN lookup first
    if isbn:
        book_info = lookup_service.get_book_info(isbn)
        if not book_info and not title:
            raise LibraryError(
                f"ISBN {isbn} not found and no manual title provided",
                status_code=400,
            )

    # Fall back to manual entry
    if not book_info:
        if not title:
            raise LibraryError("Either ISBN or title must be provided", status_code=400)

        isbn_to_use = isbn
        if not isbn_to_use:
            fake_id = str(uuid.uuid4()).replace("-", "")[:10]
            isbn_to_use = f"FAKE{fake_id}"

        book_info = BookInfo(
            isbn=isbn_to_use,
            title=title,
            authors=authors or ["Unknown Author"],
            publisher=publisher,
            published_date=published_date,
            description=description,
        )

    # Check for duplicates
    if storage.get_book(book_info.isbn):
        raise LibraryError(
            f"Book with ISBN {book_info.isbn} already exists in library",
            status_code=400,
        )

    # Optional shelf placement
    shelf_location = _validate_shelf_location(location, bookshelf_name, column, row)

    book_record = BookRecord(
        book_info=book_info,
        home_location=shelf_location,
        notes=notes,
    )

    storage.add_or_update_book(book_record)
    return book_record


def do_lookup_book(isbn: str) -> BookRecord:
    """Look up a book by ISBN from library or external sources.

    If the book exists in the library, returns the complete record with location
    and checkout status. If not in the library, performs external lookup and
    returns a BookRecord with home_location=None.
    """
    book_record = storage.get_book(isbn)
    if book_record is not None:
        return book_record

    book_info = lookup_service.get_book_info(isbn)
    if book_info is None:
        raise LibraryError(f"Book with ISBN {isbn} not found", status_code=404)

    return BookRecord(
        book_info=book_info,
        home_location=None,
        checked_out_to=None,
        checked_out_date=None,
        notes=None,
    )
