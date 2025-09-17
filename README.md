# Bookwyrms Hoard

A CLI tool for managing book collections and tracking shelf locations.

## Features

- **ISBN Lookup**: Get detailed book information from ISBN barcodes
- **Barcode Scanner Support**: Works with any barcode scanner that acts like a keyboard
- **Multiple Data Sources**: Uses Google Books API, Open Library, and other sources
- **Interactive Mode**: Perfect for scanning multiple books in succession

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

## Supported ISBN Formats

- ISBN-10: `0134685997`
- ISBN-13: `9780134685991`
- With hyphens: `978-0-13-468599-1`

The tool automatically handles format conversion and validation.

## Future Features

- [ ] Shelf location tracking
- [ ] Check-in/check-out system
- [ ] Database storage for book collection
- [ ] Search books by title/author
- [ ] Export collection data
- [ ] Web interface

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
python dev_check.py
```

### Code Quality

The codebase follows strict typing standards:

- All functions have proper type annotations
- Return types are explicitly specified
- Generic types use proper type parameters
- External library types are properly handled

## License

See LICENSE file for details.
