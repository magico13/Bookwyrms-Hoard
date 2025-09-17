"""
Command line interface for Bookwyrm's Hoard.
"""

import logging
from typing import NoReturn
import click
from .lookup import BookLookupService
from .models import BookInfo
from .shelf_models import Bookshelf, BookRecord, ShelfLocation
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


@cli.command()
def interactive() -> None:
    """Interactive mode for scanning multiple books.
    
    Perfect for use with a barcode scanner - just scan books one after another.
    Type 'quit' or 'exit' to stop.
    """
    click.echo("📚 Interactive Book Scanner Mode")
    click.echo("Scan a book barcode or type an ISBN, then press Enter.")
    click.echo("Type 'quit' or 'exit' to stop.\n")
    
    service = BookLookupService()
    
    while True:
        try:
            isbn = click.prompt("ISBN", type=str).strip()
            
            if isbn.lower() in ['quit', 'exit', 'q']:
                click.echo("👋 Goodbye!")
                break
            
            if not isbn:
                continue
                
            book_info = service.get_book_info(isbn)
            
            if book_info:
                click.echo(f"✅ Found: {book_info}")
            else:
                click.echo(f"❌ Not found: {isbn}")
            
            click.echo("-" * 40)
            
        except KeyboardInterrupt:
            click.echo("\n👋 Goodbye!")
            break
        except Exception as e:
            click.echo(f"❌ Error: {e}")


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
    click.echo("\nType 'quit' or 'exit' to stop, 'next' to move to next slot\n")
    
    service = BookLookupService()
    current_column = 0
    current_row = 0
    
    while True:
        try:
            # Show current position
            click.echo(f"📍 Current slot: Column {current_column}, Row {current_row}")
            
            # Show existing books in this slot
            existing_books = storage.get_books_on_shelf(
                location, name, current_column, current_row
            )
            if existing_books:
                click.echo("📖 Books already in this slot:")
                for book in existing_books:
                    click.echo(f"  • {book.book_info.title}")
            
            isbn = click.prompt("ISBN (or 'next'/'quit')", type=str).strip()
            
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
                continue
            
            if not isbn:
                continue
            
            # Look up book
            book_info = service.get_book_info(isbn)
            if not book_info:
                click.echo(f"❌ Book not found: {isbn}")
                continue
            
            # Create shelf location
            shelf_location = bookshelf.get_shelf_location(current_column, current_row)
            
            # Create book record
            book_record = BookRecord(
                book_info=book_info,
                home_location=shelf_location,
                current_location=shelf_location
            )
            
            # Save book
            storage.add_or_update_book(book_record)
            
            click.echo(f"✅ Added: {book_info.title}")
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
    
    if book_record.home_location and book_record.current_location:
        if (book_record.home_location.location != book_record.current_location.location or
            book_record.home_location.bookshelf_name != book_record.current_location.bookshelf_name or
            book_record.home_location.column != book_record.current_location.column or
            book_record.home_location.row != book_record.current_location.row):
            click.echo(f"🏠 Home location: {book_record.home_location}")


if __name__ == '__main__':
    cli()