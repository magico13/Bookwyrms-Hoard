"""
Command line interface for Bookwyrm's Hoard.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional
import click
from .lookup import BookLookupService
from .models import BookInfo
from .shelf_models import Bookshelf, BookRecord
from .storage import BookshelfStorage


def _display_book_info(book_info: BookInfo) -> None:
    """Display book information in a formatted way."""
    click.echo("\n" + "="*60)
    click.echo(f"Title: {book_info.title}")
    click.echo(f"Authors: {', '.join(book_info.authors) if book_info.authors else 'Unknown'}")
    
    if book_info.publisher:
        click.echo(f"Publisher: {book_info.publisher}")
    if book_info.published_date:
        click.echo(f"Published: {book_info.published_date}")
    if book_info.page_count:
        click.echo(f"Pages: {book_info.page_count}")
    if book_info.language:
        click.echo(f"Language: {book_info.language}")
    if book_info.genres:
        click.echo(f"Genres: {', '.join(book_info.genres)}")
    
    if book_info.description:
        click.echo("\nDescription:")
        # Wrap long descriptions
        desc = book_info.description[:300]
        if len(book_info.description) > 300:
            desc += "..."
        click.echo(desc)
    
    if book_info.cover_url:
        click.echo(f"\nCover Image: {book_info.cover_url}")
    
    click.echo("="*60)


def _display_brief_book_info(book_info: BookInfo) -> None:
    """Display brief book information for shelf stocking."""
    authors_str = ", ".join(book_info.authors) if book_info.authors else "Unknown Author"
    year_str = f" ({book_info.published_date})" if book_info.published_date else ""
    click.echo(f"📖 {book_info.title} by {authors_str}{year_str}")


def _generate_fake_isbn() -> str:
    """Generate a fake ISBN for books without one."""
    # Use a UUID-based approach to ensure uniqueness
    fake_id = str(uuid.uuid4()).replace('-', '')[:10]
    # Prefix with 'FAKE' to make it clear this isn't a real ISBN
    return f"FAKE{fake_id}"


def _collect_manual_book_info() -> Optional[BookInfo]:
    """Collect book information manually from user input."""
    click.echo("\n📝 Manual book entry:")
    
    title = click.prompt("Title", type=str).strip()
    if not title:
        click.echo("❌ Title is required")
        return None
    
    authors_input = click.prompt("Author(s) (separate multiple with commas)", type=str).strip()
    authors = [author.strip() for author in authors_input.split(',')] if authors_input else ["Unknown Author"]
    
    year = click.prompt("Year (optional)", type=str, default="").strip()
    
    isbn_input = click.prompt("ISBN (optional, will generate fake one if empty)", type=str, default="").strip()
    isbn = isbn_input if isbn_input else _generate_fake_isbn()
    
    book_info = BookInfo(
        isbn=isbn,
        title=title,
        authors=authors,
        published_date=year if year else None
    )
    
    return book_info


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def cli(verbose: bool) -> None:
    """Bookwyrm's Hoard - Manage your book collection and shelf locations."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)


@cli.command()
@click.argument('isbn')
def lookup(isbn: str) -> None:
    """Look up book information by ISBN.
    
    ISBN can be scanned directly from a barcode scanner or typed manually.
    Supports both ISBN-10 and ISBN-13 formats.
    """
    click.echo(f"Looking up ISBN: {isbn}")
    
    service = BookLookupService()
    book_info = service.get_book_info(isbn)
    
    if book_info:
        _display_book_info(book_info)
    else:
        click.echo(f"❌ No book information found for ISBN: {isbn}")

@cli.group()
def shelf() -> None:
    """Manage bookshelves and book locations."""
    pass


@shelf.command('create')
@click.argument('location')
@click.argument('name')
@click.option('--rows', '-r', type=int, required=True, help='Number of rows (top to bottom)')
@click.option('--columns', '-c', type=int, required=True, help='Number of columns (left to right)')
@click.option('--description', '-d', help='Optional description of the bookshelf')
def create_shelf(location: str, name: str, rows: int, columns: int, description: str) -> None:
    """Create a new bookshelf.
    
    LOCATION: Where the bookshelf is located (e.g., 'Library', 'Office')
    NAME: Name of the bookshelf (e.g., 'Large bookshelf', 'Corner shelf')
    """
    storage = BookshelfStorage()
    
    try:
        bookshelf = Bookshelf(
            location=location,
            name=name,
            rows=rows,
            columns=columns,
            description=description
        )
        
        storage.add_bookshelf(bookshelf)
        click.echo(f"✅ Created bookshelf: {bookshelf}")
        
    except ValueError as e:
        click.echo(f"❌ Error: {e}")
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}")


@shelf.command('list')
def list_shelves() -> None:
    """List all bookshelves."""
    storage = BookshelfStorage()
    bookshelves = storage.get_bookshelves()
    
    if not bookshelves:
        click.echo("No bookshelves found. Create one with 'bookwyrms shelf create'")
        return
    
    click.echo("📚 Bookshelves:")
    for bookshelf in bookshelves.values():
        click.echo(f"  • {bookshelf}")


@shelf.command('stock')
@click.argument('location')
@click.argument('name')
def stock_shelf(location: str, name: str) -> None:
    """Interactive mode for stocking a bookshelf with books.
    
    LOCATION: Location of the bookshelf
    NAME: Name of the bookshelf
    """
    storage = BookshelfStorage()
    bookshelf = storage.get_bookshelf(location, name)
    
    if not bookshelf:
        click.echo(f"❌ Bookshelf '{name}' not found in '{location}'")
        click.echo("Use 'bookwyrms shelf list' to see available bookshelves")
        return
    
    click.echo(f"📚 Stocking: {bookshelf}")
    click.echo(f"Grid: {bookshelf.columns} columns × {bookshelf.rows} rows")
    click.echo("Columns are numbered 0 to {} (left to right)".format(bookshelf.columns - 1))
    click.echo("Rows are numbered 0 to {} (top to bottom)".format(bookshelf.rows - 1))
    click.echo("\nCommands:")
    click.echo("  • Scan/type ISBN to add book")
    click.echo("  • 'manual' to manually enter book details")
    click.echo("  • 'next' to move to next slot")  
    click.echo("  • 'quit' or 'exit' to stop\n")
    
    service = BookLookupService()
    current_column = 0
    current_row = 0
    
    shown_books = False

    while True:
        try:
            # Show current position
            click.echo(f"📍 Current slot: Column {current_column}, Row {current_row}")
            
            if not shown_books:
                # Show existing books in this slot
                shown_books = True
                existing_books = storage.get_books_on_shelf(
                    location, name, current_column, current_row
                )
                if existing_books:
                    click.echo("📖 Books already in this slot:")
                    for book in existing_books:
                        _display_brief_book_info(book.book_info)
            
            isbn = click.prompt("ISBN (or 'next'/'quit'/'manual')", type=str).strip()
            
            if isbn.lower() in ['quit', 'exit', 'q']:
                click.echo("👋 Goodbye!")
                break
            
            if isbn.lower() in ['next', 'n']:
                # Move to next position (top to bottom, then left to right)
                current_row += 1
                if current_row >= bookshelf.rows:
                    current_row = 0
                    current_column += 1
                    if current_column >= bookshelf.columns:
                        click.echo("📚 Reached end of bookshelf!")
                        current_column = 0
                click.echo("-" * 40)
                shown_books = False
                continue
            
            if isbn.lower() in ['manual', 'm']:
                # Manual book entry
                book_info = _collect_manual_book_info()
                if not book_info:
                    continue
            elif not isbn:
                continue
            else:
                # Look up book by ISBN
                book_info = service.get_book_info(isbn)
                if not book_info:
                    click.echo(f"❌ Book not found: {isbn}")
                    # Offer option to enter manually
                    manual_entry = click.confirm("Would you like to enter book details manually?")
                    if manual_entry:
                        book_info = _collect_manual_book_info()
                        if not book_info:
                            continue
                    else:
                        continue
            
            # Create shelf location
            shelf_location = bookshelf.get_shelf_location(current_column, current_row)
            
            # Create book record
            book_record = BookRecord(
                book_info=book_info,
                home_location=shelf_location
            )
            
            # Save book
            storage.add_or_update_book(book_record)
            
            click.echo("✅ Added:")
            _display_brief_book_info(book_info)
            click.echo(f"📍 Location: {shelf_location}")
            click.echo("-" * 40)
            
        except KeyboardInterrupt:
            click.echo("\n👋 Goodbye!")
            break
        except Exception as e:
            click.echo(f"❌ Error: {e}")


@cli.command()
@click.argument('isbn')
def locate(isbn: str) -> None:
    """Find where a book is located.
    
    ISBN: ISBN of the book to locate
    """
    storage = BookshelfStorage()
    book_record = storage.get_book(isbn)
    
    if not book_record:
        click.echo(f"❌ Book not found: {isbn}")
        return
    
    click.echo(f"📖 {book_record.book_info.title}")
    click.echo(f"📍 {book_record.current_location_str}")
    
    # For checked out books, show where they normally belong
    if book_record.is_checked_out and book_record.home_location:
        click.echo(f"🏠 Usually kept at: {book_record.home_location}")


@cli.command('checkout')
@click.argument('isbn')
@click.argument('person')
@click.option('--date', help='Check-out date (YYYY-MM-DD), defaults to today')
def checkout_book(isbn: str, person: str, date: str) -> None:
    """Check out a book to someone.
    
    ISBN: ISBN of the book to check out
    PERSON: Name of person checking out the book
    """
    storage = BookshelfStorage()
    book_record = storage.get_book(isbn)
    
    if not book_record:
        click.echo(f"❌ Book not found: {isbn}")
        return
    
    if book_record.is_checked_out:
        click.echo(f"❌ Book is already checked out to {book_record.checked_out_to}")
        return
    
    # Use provided date or default to today
    checkout_date = date if date else datetime.now().strftime('%Y-%m-%d')
    
    # Update book record
    book_record.checked_out_to = person
    book_record.checked_out_date = checkout_date
    
    storage.add_or_update_book(book_record)
    
    click.echo(f"✅ Checked out: {book_record.book_info.title}")
    click.echo(f"👤 To: {person}")
    click.echo(f"📅 Date: {checkout_date}")


@cli.command('checkin')
@click.argument('isbn')
@click.option('--location', help='Location to check book into')
@click.option('--bookshelf', help='Bookshelf name to check book into')
@click.option('--column', type=int, help='Column number (0-based)')
@click.option('--row', type=int, help='Row number (0-based)')
def checkin_book(isbn: str, location: Optional[str], bookshelf: Optional[str], column: Optional[int], row: Optional[int]) -> None:
    """Check in a book, optionally to a new location.
    
    ISBN: ISBN of the book to check in
    
    If no location is specified, book returns to its home location.
    If location is specified, all parameters (location, bookshelf, column, row) are required.
    """
    storage = BookshelfStorage()
    book_record = storage.get_book(isbn)
    
    if not book_record:
        click.echo(f"❌ Book not found: {isbn}")
        return
    
    if not book_record.is_checked_out:
        click.echo("❌ Book is not currently checked out")
        return
    
    # Determine where to check the book in
    if location and bookshelf and column is not None and row is not None:
        # Check in to a specific new location (becomes new home location)
        target_bookshelf = storage.get_bookshelf(location, bookshelf)
        if not target_bookshelf:
            click.echo(f"❌ Bookshelf '{bookshelf}' not found in '{location}'")
            return
        
        try:
            new_location = target_bookshelf.get_shelf_location(column, row)
            book_record.home_location = new_location
            click.echo(f"📍 Checked in to new location: {new_location}")
        except ValueError as e:
            click.echo(f"❌ Invalid location: {e}")
            return
    
    elif not any([location, bookshelf, column is not None, row is not None]):
        # Check in to existing home location
        if not book_record.home_location:
            click.echo("❌ Book has no home location set. Specify location parameters.")
            return
        
        click.echo(f"🏠 Returned to home location: {book_record.home_location}")
    
    else:
        click.echo("❌ To check in to a new location, provide all: --location --bookshelf --column --row")
        return
    
    # Clear check-out information
    book_record.checked_out_to = None
    book_record.checked_out_date = None
    
    storage.add_or_update_book(book_record)
    click.echo(f"✅ Checked in: {book_record.book_info.title}")


@cli.command('status')
@click.argument('isbn', required=False)
def book_status(isbn: str) -> None:
    """Show detailed status of a book or all checked-out books.
    
    ISBN: ISBN of specific book to check (optional)
    """
    storage = BookshelfStorage()
    
    if isbn:
        # Show status of specific book
        book_record = storage.get_book(isbn)
        if not book_record:
            click.echo(f"❌ Book not found: {isbn}")
            return
        
        click.echo(f"📖 {book_record.book_info.title}")
        click.echo(f"👥 Authors: {', '.join(book_record.book_info.authors) if book_record.book_info.authors else 'Unknown'}")
        
        if book_record.is_checked_out:
            click.echo(f"📤 Status: Checked out to {book_record.checked_out_to}")
            click.echo(f"📅 Since: {book_record.checked_out_date}")
        else:
            click.echo(f"📍 Status: Available at {book_record.current_location_str}")
            if book_record.home_location:
                click.echo(f"🏠 Home: {book_record.home_location}")
    
    else:
        # Show all checked-out books
        all_books = storage.get_books()
        checked_out_books = [book for book in all_books.values() if book.is_checked_out]
        
        if not checked_out_books:
            click.echo("📚 No books are currently checked out")
            return
        
        click.echo(f"📤 Currently checked out books ({len(checked_out_books)}):")
        for book in checked_out_books:
            click.echo(f"  • {book.book_info.title}")
            click.echo(f"    👤 To: {book.checked_out_to}")
            click.echo(f"    📅 Since: {book.checked_out_date}")


@cli.command()
@click.argument('query', required=True)
def search(query: str) -> None:
    """Search for books by title, author, or ISBN.
    
    Performs case-insensitive substring matching against both title and author.
    Also supports direct ISBN lookup.
    
    Examples:
        python main.py search Python
        python main.py search "Brett Slatkin"
        python main.py search 9780134685991
    """
    storage = BookshelfStorage()
    results = storage.search_books(query)
    
    if not results:
        click.echo(f"❌ No books found matching '{query}'")
        return
    
    click.echo(f"📚 Found {len(results)} book(s) matching '{query}':")
    click.echo()
    
    for book in results:
        click.echo(f"📖 {book.book_info.title}")
        authors_str = ", ".join(book.book_info.authors) if book.book_info.authors else "Unknown Author"
        click.echo(f"   👥 By: {authors_str}")
        
        if book.book_info.published_date:
            click.echo(f"   📅 Published: {book.book_info.published_date}")
        
        # Show location/status
        if book.is_checked_out:
            click.echo(f"   📤 Status: Checked out to {book.checked_out_to}")
        else:
            click.echo(f"   📍 Location: {book.current_location_str}")
        
        click.echo(f"   🔢 ISBN: {book.book_info.isbn}")
        click.echo()


@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
@click.option('--port', default=8000, type=int, help='Port to bind to (default: 8000)')
@click.option('--reload', is_flag=True, help='Enable auto-reload for development')
def web(host: str, port: int, reload: bool) -> None:
    """Start the web API server.
    
    Provides REST API endpoints for searching books and managing the library.
    Access the interactive API documentation at http://host:port/docs
    """
    try:
        from .web_api import run_server
        click.echo(f"🚀 Starting Bookwyrm's Hoard API server...")
        click.echo(f"📡 Server will be available at: http://{host}:{port}")
        click.echo(f"📚 API documentation at: http://{host}:{port}/docs")
        if reload:
            click.echo("🔄 Auto-reload enabled for development")
        click.echo()
        run_server(host=host, port=port, reload=reload)
    except ImportError:
        click.echo("❌ FastAPI dependencies not installed.")
        click.echo("📦 Install with: pip install fastapi uvicorn")
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Failed to start server: {e}")
        raise click.Abort()


if __name__ == '__main__':
    cli()