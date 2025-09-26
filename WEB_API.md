# Bookwyrms-Hoard Web API

## Overview

The web API provides REST endpoints for searching and managing your book library. It's built with FastAPI and provides automatic interactive documentation.

## Installation

Install the additional dependencies for the web API:

```bash
pip install fastapi uvicorn
```

Or install from requirements.txt:

```bash
pip install -r requirements.txt
```

## Usage

### Starting the Server

```bash
# Start the server on default host (0.0.0.0) and port (8000)
python main.py web

# Start with custom host and port
python main.py web --host localhost --port 3000

# Start in development mode with auto-reload
python main.py web --reload
```

The server will be available at `http://localhost:8000` (or your specified host/port).

### API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## API Endpoints

### Books

#### Search Books / Get All Books

```http
GET /api/books?title=<search_term>&author=<search_term>
```

Search for books by title and/or author using case-insensitive substring matching, or get all books if no search criteria provided.

**Parameters:**

- `title` (optional): Search term for book title
- `author` (optional): Search term for author name

If no parameters are provided, returns all books in the library.

**Examples:**

```bash
# Search by title and author
curl "http://localhost:8000/api/books?title=python&author=martin"

# Search by title only
curl "http://localhost:8000/api/books?title=python"

# Get all books (no parameters)
curl "http://localhost:8000/api/books"
```

#### Get Book by ISBN

```http
GET /api/books/{isbn}
```

Retrieve a specific book by its ISBN.

**Example:**

```bash
curl "http://localhost:8000/api/books/9780134685991"
```

#### Add Book to Library

```http
POST /api/books
```

Add a new book to the library using ISBN lookup or manual entry.

**Option 1 - ISBN Lookup (recommended):**

```json
{
  "isbn": "9780134685991",
  "location": "Library",
  "bookshelf_name": "Programming",
  "column": 2,
  "row": 1,
  "notes": "Great Python book"
}
```

**Option 2 - Manual Entry:**

```json
{
  "title": "My Personal Book",
  "authors": ["John Doe", "Jane Smith"],
  "publisher": "Self Published",
  "published_date": "2025",
  "description": "A book about...",
  "location": "Office",
  "bookshelf_name": "Personal Collection",
  "column": 0,
  "row": 0
}
```

**Option 3 - Mixed (ISBN + manual fallback):**

```json
{
  "isbn": "unknown-isbn",
  "title": "Fallback Title",
  "authors": ["Backup Author"],
  "publisher": "Local Press"
}
```

**Examples:**

```bash
# Add book with ISBN lookup
curl -X POST "http://localhost:8000/api/books" \
  -H "Content-Type: application/json" \
  -d '{"isbn": "9780134685991", "location": "Library", "bookshelf_name": "Programming", "column": 0, "row": 0}'

# Add book manually (generates fake ISBN)
curl -X POST "http://localhost:8000/api/books" \
  -H "Content-Type: application/json" \
  -d '{"title": "My Book", "authors": ["Me"], "notes": "Personal copy"}'
```

**Features:**

- **Smart ISBN lookup** - Automatically fetches book details when available
- **Manual fallback** - Add books even when ISBN lookup fails
- **Optional shelf placement** - Can add with or without specific location
- **Fake ISBN generation** - Creates unique identifiers for books without ISBNs
- **Duplicate prevention** - Won't add books that already exist

**Error Cases:**

- 400: Neither ISBN nor title provided
- 400: ISBN not found and no title provided
- 400: Book already exists in library
- 400: Invalid shelf location (shelf doesn't exist or coordinates out of bounds)

#### Check Out Book

```http
POST /api/books/{isbn}/checkout
```

Check out a book to a person. Sets `checked_out_to` and `checked_out_date` fields.

**Request Body:**

```json
{
  "checked_out_to": "John Doe"
}
```

**Example:**

```bash
curl -X POST "http://localhost:8000/api/books/9780134685991/checkout" \
  -H "Content-Type: application/json" \
  -d '{"checked_out_to": "John Doe"}'
```

**Error Cases:**

- 404: Book not found
- 400: Book already checked out

#### Check In Book

```http
POST /api/books/{isbn}/checkin
```

Check in a book, optionally relocating it to a new shelf position.

**Option 1 - Simple Check-in (no request body):**
Returns book to its current home location.

```bash
curl -X POST "http://localhost:8000/api/books/9780134685991/checkin"
```

**Option 2 - Check-in with Relocation:**

```json
{
  "location": "Library",
  "bookshelf_name": "Large Shelf",
  "column": 2,
  "row": 1
}
```

```bash
curl -X POST "http://localhost:8000/api/books/9780134685991/checkin" \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Library",
    "bookshelf_name": "Large Shelf", 
    "column": 2,
    "row": 1
  }'
```

**Error Cases:**

- 404: Book not found
- 400: Book not checked out
- 400: Invalid location (bookshelf doesn't exist or coordinates out of bounds)
- 400: Incomplete location (if relocating, all fields required)

### Shelves

#### Get All Shelves

```http
GET /api/shelves
```

Retrieve all bookshelves in the library.

**Example:**

```bash
curl "http://localhost:8000/api/shelves"
```

#### Get Specific Shelf

```http
GET /api/shelves/{location}/{name}
```

Retrieve a specific bookshelf by location and name.

**Parameters:**

- `location`: The location where the bookshelf is located (e.g., 'Library')
- `name`: The name of the bookshelf (e.g., 'Large bookshelf')

**Example:**

```bash
curl "http://localhost:8000/api/shelves/Library/Programming%20Shelf"
```

**Error Cases:**

- 404: Bookshelf not found

#### Create New Shelf

```http
POST /api/shelves
```

Create a new bookshelf in the library.

**Request Body:**

```json
{
  "location": "Library",
  "name": "New Programming Shelf",
  "rows": 5,
  "columns": 4,
  "description": "Shelf for programming books"
}
```

**Example:**

```bash
curl -X POST "http://localhost:8000/api/shelves" \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Library",
    "name": "Programming Shelf",
    "rows": 5,
    "columns": 4,
    "description": "Books about programming"
  }'
```

**Features:**

- **Grid-based positioning** - Specify rows and columns for book organization
- **Optional descriptions** - Add notes about what the shelf contains
- **Duplicate prevention** - Won't create shelves with same location/name combination

**Error Cases:**

- 400: Bookshelf already exists in that location
- 400: Invalid dimensions (rows/columns must be positive integers)

#### Delete Shelf

```http
DELETE /api/shelves/{location}/{name}
```

Delete a bookshelf from the library.

**Parameters:**

- `location`: The location where the bookshelf is located
- `name`: The name of the bookshelf to delete

**Example:**

```bash
curl -X DELETE "http://localhost:8000/api/shelves/Library/Old%20Shelf"
```

**Important:** Shelves with books assigned to them cannot be deleted. You must relocate all books first.

**Error Cases:**

- 404: Bookshelf not found
- 400: Bookshelf has books assigned (includes count of books)

### System

#### Health Check

```http
GET /api/health
```

Simple health check endpoint.

#### Root

```http
GET /
```

API information and version.

## Response Format

All book data is returned as JSON with the following structure:

```json
{
  "book_info": {
    "isbn": "9780134685991",
    "title": "Effective Python",
    "authors": ["Brett Slatkin"],
    "publisher": "Addison-Wesley",
    "published_date": "2019",
    "description": "...",
    "genres": ["Programming"],
    "page_count": 352,
    "cover_url": "https://...",
    "language": "en"
  },
  "home_location": {
    "location": "Library",
    "bookshelf_name": "Programming",
    "column": 2,
    "row": 1
  },
  "checked_out_to": null,
  "checkout_date": null,
  "notes": ""
}
```

## Testing

### Test Data Management

To safely test the API without modifying your production library data, use the provided test dataset:

```bash
# Switch to test data (5 books, 2 shelves)
./switch_data.sh test

# Check current data status
./switch_data.sh status

# Switch back to production data
./switch_data.sh production
```

### Test Dataset

The test data includes:

- **5 test books** with predictable ISBNs for easy testing
- **2 test bookshelves** (Library/Test Shelf, Office/Small Shelf)
- **1 pre-checked-out book** for testing error scenarios

**Test ISBNs you can use:**

- `9780134685991` - Effective Python (available)
- `9780262046305` - Introduction to Algorithms (available)
- `9781491950296` - Programming Rust (available)
- `TEST123456789` - The Art of Testing APIs (available)
- `CHECKED456789` - Already Checked Out Book (pre-checked out)

**Data Files:**

- `data/books.json` / `data/bookshelves.json` - Active data (what API uses)
- `data/books_production.json` / `data/bookshelves_production.json` - Production backup
- `data/books_test.json` / `data/bookshelves_test.json` - Safe test dataset

### Running Tests

Basic test script:

```bash
# Start the server in one terminal
python main.py web --reload

# Switch to test data and run basic tests
./switch_data.sh test
python test_api_comprehensive.py
```

Comprehensive test script:

```bash
# Comprehensive API testing with test data
./switch_data.sh test
python test_api_comprehensive.py
```

### Data Safety

- **Production data** is backed up to `data/books_production.json` and `data/bookshelves_production.json`
- **Test data** is isolated in `data/books_test.json` and `data/bookshelves_test.json`
- **Active data** files (`data/books.json`, `data/bookshelves.json`) are what the API uses
- Use `./switch_data.sh` to safely switch between datasets

## Docker Support

The API is designed to run in Docker containers. See the main README for Docker setup instructions.
