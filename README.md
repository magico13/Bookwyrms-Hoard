# Bookwyrm's Hoard

A CLI tool for managing book collections and tracking shelf locations.

## Features

- **ISBN Lookup**: Get detailed book information from ISBN barcodes
- **Barcode Scanner Support**: Works with any barcode scanner that acts like a keyboard
- **Multiple Data Sources**: Uses Google Books API, Open Library, and other sources
- **Interactive Mode**: Perfect for scanning multiple books in succession
- **Smart Search**: Search your library by ISBN, title, or author with intelligent detection
- **Shelf Management**: Create and organize bookshelves with grid-based locations
- **Book Location Tracking**: Track where each book is located on your shelves
- **Check-out System**: Check books out to people and track due dates
- **Web API**: Complete REST API for programmatic access
- **MCP Server Support**: Model Context Protocol server for AI assistant integration
- **CORS Support**: Cross-origin requests enabled for web integrations
- **SQLite + FTS Search**: Fast, portable database storage with full-text search (legacy JSON support preserved for migration)

## Installation

1. Clone this repository
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. **Optional**: Set up Google Books API key for higher rate limits:
   - Copy `.env.example` to `.env`
   - Get an API key from [Google Cloud Console](https://console.cloud.google.com/)
   - Enable the Books API in your project
   - Add your API key to the `.env` file:

     ```bash
     GOOGLE_BOOKS_API_KEY=your_api_key_here
     ```

## Usage

### Single Book Lookup

```bash
python main.py lookup 9780134685991
```

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

Books and shelf information now live in a single SQLite database (`data/books.db`) that powers both the CLI and the FastAPI server. The database ships with SQLite's FTS5 extension enabled so searches like `"Edward Ashton 4th Consort"` can rank the most relevant matches even when the query mixes title/author fragments.

### Migrating from JSON (one-time)

If you're upgrading from an older release that used `books.json` / `bookshelves.json`, run the migration script once:

```bash
python scripts/migrate_json_to_sqlite.py --json-dir data --db-path data/books.db --force
```

The script automatically backs up existing `.db` files (or creates them if missing) and copies every shelf/book into SQLite. A legacy `JSONBookshelfStorage` lives in `bookwyrms/storage_json.py` purely for this migration path.

### Switching between datasets

Use `switch_data.sh` to swap between production/test databases or create backups:

```bash
# Switch to the curated test dataset
./switch_data.sh test

# Switch back to your production data
./switch_data.sh production

# See which DB is active and how many rows it has
./switch_data.sh status
```

The script copies between `data/books.db`, `data/books_test.db`, and `data/books_production.db`. If the test/prod DBs don't exist yet, it will tell you how to generate them via the migration script using the JSON fixtures that remain in `data/` for reference.

### Custom database locations

Set the `BOOKWYRMS_DB_PATH` environment variable (or pass `db_path` into `BookshelfStorage`) to point the app at a different SQLite file. This is useful for Docker volumes, CI runs, or experimental datasets:

```bash
export BOOKWYRMS_DB_PATH=/tmp/bookwyrms-dev.db
python main.py search dune
```

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
- **CORS support**: Cross-origin requests enabled for web integrations
- **MCP server integration**: Model Context Protocol endpoints for AI assistant integration

See [WEB_API.md](WEB_API.md) for complete API documentation and examples.

## MCP Server Support

Bookwyrm's Hoard includes basic Model Context Protocol (MCP) server support for integration with AI assistants and LLMs:

**MCP Endpoints:**

- `/api/books` - Search and retrieve books
- `/api/shelves` - List bookshelves

**Features:**

- **Smart Search**: AI assistants can search your library by title, author, or ISBN
- **Shelf Discovery**: Browse your bookshelf organization and layout
- **CORS Enabled**: Supports cross-origin requests from MCP clients
- **Standardized API**: RESTful endpoints compatible with MCP specifications

## Docker Deployment

The easiest way to run Bookwyrm's Hoard is using Docker:

### Quick Start

```bash
# Clone the repository
git clone https://github.com/magico13/Bookwyrms-Hoard.git
cd Bookwyrms-Hoard

# Start the web server
docker-compose up --build
```

The web interface will be available at `http://localhost:8000`

### Docker Commands

```bash
# Build and start the container
docker-compose up --build

# Run in the background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

### Data Persistence

Your library data is stored in the `data/` directory and automatically persists between container restarts. The `data/` directory will be created automatically when you first run the container.

**Note**: The Docker container uses `requirements-docker.txt` which includes only production dependencies, excluding development tools like mypy and type stubs.

### Custom Configuration

You can customize the port by editing the `docker-compose.yml` file:

```yaml
ports:
  - "3000:8000"  # Access on port 3000 instead of 8000
```

## Development

This project uses:

- **isbnlib**: ISBN validation and metadata lookup
- **requests**: HTTP API calls
- **click**: Command-line interface framework
- **SQLAlchemy**: SQLite schema management and query builder
- **FastAPI**: Web API framework with automatic OpenAPI documentation
- **uvicorn**: ASGI web server for production deployment
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
