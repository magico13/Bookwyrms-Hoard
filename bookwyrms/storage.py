"""
Storage manager for bookshelves and book records.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from .shelf_models import Bookshelf, BookRecord

logger = logging.getLogger(__name__)


class BookshelfStorage:
    """Manages storage of bookshelves and book records in JSON files."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize storage manager.
        
        Args:
            data_dir: Directory to store data files. Defaults to ./data/
        """
        if data_dir is None:
            data_dir = Path.cwd() / "data"
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.bookshelves_file = self.data_dir / "bookshelves.json"
        self.books_file = self.data_dir / "books.json"
        
        # Cache for loaded data
        self._bookshelves: Optional[Dict[str, Bookshelf]] = None
        self._books: Optional[Dict[str, BookRecord]] = None
    
    def _load_bookshelves(self) -> Dict[str, Bookshelf]:
        """Load bookshelves from JSON file."""
        if not self.bookshelves_file.exists():
            return {}
        
        try:
            with open(self.bookshelves_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            bookshelves = {}
            for shelf_id, shelf_data in data.items():
                bookshelves[shelf_id] = Bookshelf.from_dict(shelf_data)
            
            return bookshelves
            
        except Exception as e:
            logger.error(f"Error loading bookshelves: {e}")
            return {}
    
    def _save_bookshelves(self, bookshelves: Dict[str, Bookshelf]) -> None:
        """Save bookshelves to JSON file."""
        try:
            data = {}
            for shelf_id, bookshelf in bookshelves.items():
                data[shelf_id] = bookshelf.to_dict()
            
            with open(self.bookshelves_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Error saving bookshelves: {e}")
            raise
    
    def _load_books(self) -> Dict[str, BookRecord]:
        """Load book records from JSON file."""
        if not self.books_file.exists():
            return {}
        
        try:
            with open(self.books_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            books = {}
            for isbn, book_data in data.items():
                books[isbn] = BookRecord.from_dict(book_data)
            
            return books
            
        except Exception as e:
            logger.error(f"Error loading books: {e}")
            return {}
    
    def _save_books(self, books: Dict[str, BookRecord]) -> None:
        """Save book records to JSON file."""
        try:
            data = {}
            for isbn, book_record in books.items():
                data[isbn] = book_record.to_dict()
            
            with open(self.books_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Error saving books: {e}")
            raise
    
    def get_bookshelves(self) -> Dict[str, Bookshelf]:
        """Get all bookshelves."""
        if self._bookshelves is None:
            self._bookshelves = self._load_bookshelves()
        return self._bookshelves.copy()
    
    def get_bookshelf(self, location: str, name: str) -> Optional[Bookshelf]:
        """Get a specific bookshelf."""
        shelf_id = f"{location}#{name}"
        bookshelves = self.get_bookshelves()
        return bookshelves.get(shelf_id)
    
    def add_bookshelf(self, bookshelf: Bookshelf) -> None:
        """Add a new bookshelf."""
        if self._bookshelves is None:
            self._bookshelves = self._load_bookshelves()
        
        shelf_id = f"{bookshelf.location}#{bookshelf.name}"
        
        if shelf_id in self._bookshelves:
            raise ValueError(f"Bookshelf '{bookshelf.name}' already exists in '{bookshelf.location}'")
        
        self._bookshelves[shelf_id] = bookshelf
        self._save_bookshelves(self._bookshelves)
        logger.info(f"Added bookshelf: {bookshelf}")
    
    def remove_bookshelf(self, location: str, name: str) -> bool:
        """Remove a bookshelf."""
        if self._bookshelves is None:
            self._bookshelves = self._load_bookshelves()
        
        shelf_id = f"{location}#{name}"
        
        if shelf_id not in self._bookshelves:
            return False
        
        # Check if any books are assigned to this bookshelf
        books = self.get_books()
        books_on_shelf = [
            book for book in books.values()
            if (book.home_location and 
                book.home_location.location == location and 
                book.home_location.bookshelf_name == name)
        ]
        
        if books_on_shelf:
            raise ValueError(f"Cannot remove bookshelf '{name}' - it has {len(books_on_shelf)} books assigned")
        
        del self._bookshelves[shelf_id]
        self._save_bookshelves(self._bookshelves)
        logger.info(f"Removed bookshelf: {location}/{name}")
        return True
    
    def get_books(self) -> Dict[str, BookRecord]:
        """Get all book records."""
        if self._books is None:
            self._books = self._load_books()
        return self._books.copy()
    
    def get_book(self, isbn: str) -> Optional[BookRecord]:
        """Get a specific book record."""
        books = self.get_books()
        return books.get(isbn)
    
    def add_or_update_book(self, book_record: BookRecord) -> None:
        """Add or update a book record."""
        if self._books is None:
            self._books = self._load_books()
        
        isbn = book_record.book_info.isbn
        self._books[isbn] = book_record
        self._save_books(self._books)
        
        action = "Updated" if isbn in self._books else "Added"
        logger.info(f"{action} book: {book_record.book_info.title}")
    
    def remove_book(self, isbn: str) -> bool:
        """Remove a book record."""
        if self._books is None:
            self._books = self._load_books()
        
        if isbn not in self._books:
            return False
        
        title = self._books[isbn].book_info.title
        del self._books[isbn]
        self._save_books(self._books)
        logger.info(f"Removed book: {title}")
        return True
    
    def get_books_on_shelf(self, location: str, bookshelf_name: str, 
                          column: Optional[int] = None, row: Optional[int] = None) -> List[BookRecord]:
        """Get books on a specific shelf location."""
        books = self.get_books()
        result = []
        
        for book in books.values():
            book_location = book.current_location or book.home_location
            if not book_location:
                continue
            
            if (book_location.location == location and 
                book_location.bookshelf_name == bookshelf_name):
                
                if column is not None and book_location.column != column:
                    continue
                if row is not None and book_location.row != row:
                    continue
                
                result.append(book)
        
        return result