"""SQLite schema helpers for Bookwyrm's Hoard."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    event,
    text,
)
from sqlalchemy.engine import Engine

LIST_DELIMITER: Final[str] = "||"

metadata = MetaData()

bookshelves_table = Table(
    "bookshelves",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("location", Text, nullable=False),
    Column("name", Text, nullable=False),
    Column("rows", Integer, nullable=False),
    Column("columns", Integer, nullable=False),
    Column("description", Text, nullable=True),
)

books_table = Table(
    "books",
    metadata,
    Column("isbn", Text, primary_key=True),
    Column("title", Text, nullable=False),
    Column("authors", Text, nullable=False),
    Column("publisher", Text, nullable=True),
    Column("published_date", Text, nullable=True),
    Column("description", Text, nullable=True),
    Column("genres", Text, nullable=True),
    Column("page_count", Integer, nullable=True),
    Column("cover_url", Text, nullable=True),
    Column("language", Text, nullable=True),
    Column("home_bookshelf_id", ForeignKey("bookshelves.id", ondelete="SET NULL"), nullable=True),
    Column("home_column", Integer, nullable=True),
    Column("home_row", Integer, nullable=True),
    Column("checked_out_to", Text, nullable=True),
    Column("checked_out_date", Text, nullable=True),
    Column("notes", Text, nullable=True),
    Column("created_at", Text, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
    Column("updated_at", Text, nullable=False, server_default=text("CURRENT_TIMESTAMP")),
)


def create_sqlite_engine(db_path: Path) -> Engine:
    """Create a SQLite engine for the provided path."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )

    def _set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    event.listen(engine, "connect", _set_sqlite_pragma)

    return engine


def initialize_database(engine: Engine) -> None:
    """Create tables, FTS index, and triggers if they do not exist."""
    with engine.begin() as conn:
        metadata.create_all(conn)

        conn.exec_driver_sql(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_bookshelves_location_name
            ON bookshelves(location, name);
            """
        )

        conn.exec_driver_sql(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS books_fts USING fts5(
                isbn UNINDEXED,
                title,
                authors,
                description
            );
            """
        )

        conn.exec_driver_sql(
            """
            CREATE TRIGGER IF NOT EXISTS books_ai AFTER INSERT ON books BEGIN
                INSERT INTO books_fts(isbn, title, authors, description)
                VALUES (new.isbn, new.title, new.authors, COALESCE(new.description, ''));
            END;
            """
        )

        conn.exec_driver_sql(
            """
            CREATE TRIGGER IF NOT EXISTS books_ad AFTER DELETE ON books BEGIN
                DELETE FROM books_fts WHERE isbn = old.isbn;
            END;
            """
        )

        conn.exec_driver_sql(
            """
            CREATE TRIGGER IF NOT EXISTS books_au AFTER UPDATE ON books BEGIN
                DELETE FROM books_fts WHERE isbn = old.isbn;
                INSERT INTO books_fts(isbn, title, authors, description)
                VALUES (new.isbn, new.title, new.authors, COALESCE(new.description, ''));
            END;
            """
        )


def utcnow_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()
