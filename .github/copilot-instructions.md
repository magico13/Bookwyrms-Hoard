# Bookwyrms-Hoard AI Coding Instructions

## Architecture Overview

This is a **type-safe Python CLI tool** for personal library management with barcode scanner support. The architecture follows domain separation principles:

- `bookwyrms/models.py` - Core book metadata (`BookInfo` dataclass)  
- `bookwyrms/shelf_models.py` - Physical shelf management (`Bookshelf`, `ShelfLocation`, `BookRecord`)
- `bookwyrms/lookup.py` - Multi-source ISBN lookup service (isbnlib → Google Books API fallback)
- `bookwyrms/storage.py` - JSON file persistence in `data/` directory
- `bookwyrms/cli.py` - Click-based command interface with interactive modes

## Critical Patterns

### Location System
Books use a **grid-based coordinate system** (0-indexed):
- Format: `Location/Bookshelf/C{column}R{row}` (e.g., `Library/Large bookshelf/C2R1`)
- **Home location**: Where book belongs on the shelf
- Books not on shelves are tracked via `checked_out_to` field

### ISBN Handling
- Supports ISBN-10, ISBN-13, with/without hyphens via `isbnlib.canonical()`
- **Fake ISBN generation**: `FAKE{uuid[:10]}` for books without ISBNs using `_generate_fake_isbn()`
- Lookup precedence: isbnlib services ('goob', 'openl') → Google Books API direct

### Data Serialization
All domain objects are **dataclasses** with consistent `to_dict()`/`from_dict()` patterns for JSON persistence in `data/books.json` and `data/bookshelves.json`.

## Development Workflow

### Type Checking
**Extremely strict mypy configuration** - all functions must have complete type annotations:
```bash
python dev_check.py              # Run mypy + basic functionality test
python dev_check.py --check-updates    # Also check for package updates
python -m mypy bookwyrms/ main.py      # Direct mypy execution
```

### Interactive vs Single-Shot Modes
- `python main.py shelf stock <location> <bookshelf>` - Interactive barcode scanning mode for stocking shelves
- `python main.py lookup <isbn>` - Single book lookup

### Adding New Commands
Follow the Click pattern in `cli.py`:
1. Create `@cli.command()` function with proper type hints
2. Use `BookshelfStorage()` for persistence operations  
3. Call `BookLookupService().get_book_info()` for ISBN lookups
4. Display with `_display_book_info()` or `_display_brief_book_info()`

## Key Integration Points

- **External APIs**: Google Books API, Open Library (via isbnlib)
- **File System**: JSON files in `data/` directory (created automatically)
- **User Input**: Interactive barcode scanning via `shelf stock` command, manual book entry via `_collect_manual_book_info()`

## Common Operations

```python
# Load/save data
storage = BookshelfStorage()
books = storage.get_all_books()
storage.save_book_record(book_record)

# ISBN lookup with fallback
service = BookLookupService()
book_info = service.get_book_info(isbn)  # Returns None if not found

# Create shelf location
shelf = Bookshelf("Library", "Large bookshelf", rows=5, columns=4)
location = shelf.get_shelf_location(column=2, row=1)  # Validates bounds
```

When extending functionality, maintain the strict typing discipline and domain separation. All new code should pass `python dev_check.py` without warnings.