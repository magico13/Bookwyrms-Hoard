# Bookwyrm's Hoard

A CLI tool for managing book collections and tracking shelf locations.

## Features

- **ISBN Lookup**: Get detailed book information from ISBN barcodes
- **Barcode Scanner Support**: Works with any barcode scanner that acts like a keyboard
- **Multiple Data Sources**: Uses Google Books API, Open Library, and other sources
- **Interactive Mode**: Perfect for scanning multiple books in succession
- **Book Search**: Search your library by title and/or author
- **Shelf Management**: Create and organize bookshelves with grid-based locations
- **Book Location Tracking**: Track where each book is located on your shelves
- **Check-out System**: Check books out to people and track due dates
- **Web API**: Complete REST API for programmatic access
- **JSON Storage**: Portable data storage that works with version control

## Installation

1. Clone this repository
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Single Book Lookup

```bash
python main.py lookup 9780134685991
```

### Interactive Scanner Mode

```bash
python main.py interactive
```

This will start an interactive session where you can scan book barcodes one after another. Perfect for use with a dedicated barcode scanner.

### Bookshelf Management

```bash
# Create a bookshelf
python main.py shelf create "Library" "Large bookshelf" --rows 5 --columns 4

# List all bookshelves
python main.py shelf list

# Interactive shelf stocking
python main.py shelf stock "Library" "Large bookshelf"

# Find where a book is located
python main.py locate 9780134685991
```

### Bookshelf Organization

Bookshelves are organized in a grid system:

- **Columns**: Numbered 0 to N from left to right
- **Rows**: Numbered 0 to N from top to bottom
- **Location Format**: `Location/Bookshelf/C{column}R{row}`

Example: A book at `Library/Large bookshelf/C2R1` is in the Library, on the Large bookshelf, 3rd column from left, 2nd row from top.

## Supported ISBN Formats

- ISBN-10: `0134685997`
- ISBN-13: `9780134685991`
- With hyphens: `978-0-13-468599-1`

The tool automatically handles format conversion and validation.

### Check-out System

```bash
# Check out a book to someone
python main.py checkout 9780134685991 "John Doe"

# Check out with custom date
python main.py checkout 9780134685991 "Jane Smith" --date 2025-01-01

# Check in to home location
python main.py checkin 9780134685991

# Check in to specific location
python main.py checkin 9780134685991 --location Library --bookshelf "Large bookshelf" --column 0 --row 1

# Check book status
python main.py status 9780134685991

# List all checked-out books
python main.py status
```

## Data Storage

Books and shelf information are stored in JSON files in the `data/` directory:

- `data/books.json`: Book records with locations and checkout status
- `data/bookshelves.json`: Bookshelf definitions and configurations

## Web API

A full REST API is available for programmatic access to your library:

```bash
# Start the web API server
python main.py web

# Or with auto-reload for development
python main.py web --reload
```

**Features:**

- **Complete book management**: Add, search, checkout, and check-in books
- **Shelf management**: Create, list, and delete bookshelves
- **ISBN lookup integration**: Automatic book metadata retrieval
- **Interactive documentation**: Available at `http://localhost:8000/docs`

See [WEB_API.md](WEB_API.md) for complete API documentation and examples.

## Future Features

- [ ] Import/export collection data
- [ ] Web interface frontend

## Development

This project uses:

- **isbnlib**: ISBN validation and metadata lookup
- **requests**: HTTP API calls
- **click**: Command-line interface framework
- **mypy**: Static type checking for Python

### Type Checking

This project uses comprehensive type hints throughout the codebase. To run type checking:

```bash
python -m mypy bookwyrms/ main.py
```

Or use the development check script:

```bash
# Run type checking and functionality tests
python dev_check.py

# Also check for package updates
python dev_check.py --check-updates

# Only check for package updates
python dev_check.py --updates-only
```

### Code Quality

The codebase follows strict typing standards:

- All functions have proper type annotations
- Return types are explicitly specified
- Generic types use proper type parameters
- External library types are properly handled

## License

See LICENSE file for details.
