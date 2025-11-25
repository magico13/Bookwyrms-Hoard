# SQLite/FTS5 Migration Plan

## Goals

- Replace JSON-based `BookshelfStorage` with a SQLite-backed implementation that supports FTS5 search.
- Maintain existing CLI and FastAPI behaviors with minimal interface changes.
- Provide one-time migration for production JSON data and a workflow for switching between production/test datasets.

## Schema Overview

### Tables

1. `bookshelves`
   - `id INTEGER PRIMARY KEY`
   - `location TEXT NOT NULL`
   - `name TEXT NOT NULL`
   - `rows INTEGER NOT NULL`
   - `columns INTEGER NOT NULL`
   - `description TEXT`
   - `UNIQUE(location, name)` to enforce one shelf per location/name pair.


2. `books`
   - `isbn TEXT PRIMARY KEY`
   - `title TEXT NOT NULL`
   - `authors TEXT NOT NULL` (authors joined with `"||"`)
   - `publisher TEXT`
   - `published_date TEXT`
   - `description TEXT`
   - `genres TEXT` (joined with `"||"`)
   - `page_count INTEGER`
   - `cover_url TEXT`
   - `language TEXT`
   - `home_bookshelf_id INTEGER` (FK -> `bookshelves.id`)
   - `home_column INTEGER`
   - `home_row INTEGER`
   - `checked_out_to TEXT`
   - `checked_out_date TEXT` (store ISO-8601 UTC, convert to local time only for display)
   - `notes TEXT`
   - `created_at DATETIME DEFAULT CURRENT_TIMESTAMP`
   - `updated_at DATETIME DEFAULT CURRENT_TIMESTAMP`
   - Trigger to refresh `updated_at` on UPDATE.


3. `books_fts` (virtual table)
   - `CREATE VIRTUAL TABLE books_fts USING fts5(isbn UNINDEXED, title, authors, description)`
   - SQLite triggers on INSERT/UPDATE/DELETE repopulate the FTS rows so search stays in sync with `books` and we can join on `isbn`.

> **Future enhancement**: add a `contacts` table (`id INTEGER PRIMARY KEY`, `name TEXT UNIQUE NOT NULL`) to store frequent checkout recipients, then reference it from `books.checked_out_to_contact_id`. For the initial migration we can keep the existing free-form `checked_out_to TEXT` to avoid blocking the storage swap.

## Data Access Layer

- Introduce `bookwyrms/db.py` with SQLAlchemy Core definitions (engine factory, metadata, tables, helper functions).
- Implement `SQLiteStorage` mirroring the existing `BookshelfStorage` interface (same public methods) but backed by SQL queries.
- Respect a `BOOKWYRMS_DB_PATH` environment variable so Docker/test runs can point at alternate databases without code changes.
- Search implementation:
  - Tokenize user query into `token*` fragments for prefix matching.
  - Run `SELECT b.*, bm25(books_fts) AS score FROM books_fts JOIN books b ON b.isbn = books_fts.isbn WHERE books_fts MATCH :match ORDER BY bm25(...) LIMIT :n`.
  - Optional post-filter using `editdist3()` when the SQLite build includes spellfix (nice-to-have only).

## Migration Strategy

1. **Dependencies**: add `sqlalchemy>=2` (and `aiosqlite` if async ever needed) to `requirements.txt`/`pyproject.toml`.
2. **Bootstrap script**: `scripts/init_sqlite.py` lets us explicitly pre-create databases (helpful for CI or Docker images); storage auto-initializes as well.
3. **One-time migration**: `scripts/migrate_json_to_sqlite.py`
   - Loads shelves/books via current JSON `BookshelfStorage`.
   - Inserts shelves first, capturing their generated IDs.
   - Inserts books, translating authors/genres into delimiter strings and setting `home_bookshelf_id` based on location/name lookup.
   - Uses normal INSERTs so triggers populate `books_fts`.
   - Options: `--src-dir data/`, `--dst data/books.db`, `--force` to overwrite existing DB, `--dry-run`.
   - Relies on `bookwyrms/storage_json.py` which retains the legacy JSON implementation under the `JSONBookshelfStorage` name.
4. **switch_data.sh**: now copies between SQLite files (`books.db`, `books_test.db`, `books_production.db`) and guides users to run the migration script if the per-environment DBs are missing.
5. **Application wiring**:
   - Swap imports in CLI/Web API to use `SQLiteStorage`.
   - Provide env var/CLI option for DB path (default `data/books.db`).
   - Ensure FastAPI startup uses the same storage singleton.
6. **Testing**:
   - Add storage integration tests using a temporary SQLite file.
   - Verify `dev_check.py` either seeds a temp DB or points to the test DB file.
7. **Documentation**:
   - Update README/WEB_API with new storage requirements, backup commands (`sqlite3 data/books.db ".backup books-$(date +%Y%m%d).db"`).
   - Document migration steps: run script, verify, remove JSON.

## Work Breakdown

1. Implement SQLAlchemy schema + storage class.
2. Inject new storage into CLI and API, keeping method signatures stable.
3. Write migration script and test on sample data.
4. Update scripts (`switch_data.sh`), docs, and add dependency changes.
5. Run end-to-end tests (CLI commands, API search) against migrated DB.

## Open Questions / Follow-ups

- Confirm delimiter (`"||"`) is acceptable for authors/genres.
- Decide whether to ship a pre-built `books_test.db` or generate it on demand for CI/tests.
- Determine if `editdist3()` is available in deployment SQLite; if not, fallback to pure FTS ranking.
