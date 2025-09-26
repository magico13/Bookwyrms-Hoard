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
```
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
```
GET /api/books/{isbn}
```

Retrieve a specific book by its ISBN.

**Example:**
```bash
curl "http://localhost:8000/api/books/9780134685991"
```

#### Check Out Book
```
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
```
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

### System

#### Health Check
```
GET /api/health
```

Simple health check endpoint.

#### Root
```
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

### Running Tests

Basic test script:
```bash
# Start the server in one terminal
python main.py web --reload

# Switch to test data and run basic tests
./switch_data.sh test
python test_web_api.py
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