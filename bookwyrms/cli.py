"""
Command line interface for Bookwyrm's Hoard.
"""

import logging
import click
from .lookup import BookLookupService
from .models import BookInfo


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


if __name__ == '__main__':
    cli()