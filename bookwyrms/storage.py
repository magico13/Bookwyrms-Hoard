"""SQLite-backed storage manager for bookshelves and book records."""

from __future__ import annotations

import logging
import os
import re
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import Select, and_, func, or_, select, text
from sqlalchemy.engine import Engine, RowMapping
from sqlalchemy.exc import IntegrityError

from .db import (
    LIST_DELIMITER,
    books_table,
    bookshelves_table,
    create_sqlite_engine,
    initialize_database,
    utcnow_iso,
)
from .models import BookInfo
from .shelf_models import BookRecord, Bookshelf, ShelfLocation

logger = logging.getLogger(__name__)

DEFAULT_DB_FILENAME = "books.db"
SEARCH_LIMIT = 50


def _split_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item for item in value.split(LIST_DELIMITER) if item]


def _join_list(values: Sequence[str]) -> str:
    sanitized = [value.strip() for value in values if value.strip()]
    if not sanitized:
        return "Unknown Author"
    return LIST_DELIMITER.join(sanitized)


def _join_optional_list(values: Optional[Sequence[str]]) -> Optional[str]:
    if not values:
        return None
    sanitized = [value.strip() for value in values if value.strip()]
    if not sanitized:
        return None
    return LIST_DELIMITER.join(sanitized)


def _tokenize_query(query: str) -> List[str]:
    tokens = re.findall(r"[0-9A-Za-z]+", query)
    return [token.lower() for token in tokens if token]


class BookshelfStorage:
    """SQLite-backed persistence adapter for shelves and books."""

    def __init__(self, db_path: Optional[Path] = None):
        env_path = os.environ.get("BOOKWYRMS_DB_PATH")
        if db_path is None and env_path:
            db_path = Path(env_path)

        if db_path is None:
            data_dir = Path.cwd() / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = data_dir / DEFAULT_DB_FILENAME

        self.db_path = Path(db_path)
        self.engine: Engine = create_sqlite_engine(self.db_path)
        initialize_database(self.engine)
        self._legacy_warning_emitted = False
        self._maybe_warn_about_legacy_json()

    # ------------------------------------------------------------------
    # Shelf helpers
    # ------------------------------------------------------------------
    def get_bookshelves(self) -> Dict[str, Bookshelf]:
        stmt = select(bookshelves_table).order_by(
            bookshelves_table.c.location, bookshelves_table.c.name
        )
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).all()

        shelves: Dict[str, Bookshelf] = {}
        for row in rows:
            shelf = Bookshelf(
                location=row.location,
                name=row.name,
                rows=row.rows,
                columns=row.columns,
                description=row.description,
            )
            shelves[f"{shelf.location}#{shelf.name}"] = shelf
        return shelves

    def get_bookshelf(self, location: str, name: str) -> Optional[Bookshelf]:
        stmt = select(bookshelves_table).where(
            and_(
                bookshelves_table.c.location == location,
                bookshelves_table.c.name == name,
            )
        )
        with self.engine.connect() as conn:
            row = conn.execute(stmt).mappings().one_or_none()

        if row is None:
            return None

        return Bookshelf(
            location=row["location"],
            name=row["name"],
            rows=row["rows"],
            columns=row["columns"],
            description=row["description"],
        )

    def add_bookshelf(self, bookshelf: Bookshelf) -> None:
        with self.engine.begin() as conn:
            try:
                conn.execute(
                    bookshelves_table.insert().values(
                        location=bookshelf.location,
                        name=bookshelf.name,
                        rows=bookshelf.rows,
                        columns=bookshelf.columns,
                        description=bookshelf.description,
                    )
                )
            except IntegrityError as exc:  # pragma: no cover - DB constraint
                raise ValueError(
                    f"Bookshelf '{bookshelf.name}' already exists in '{bookshelf.location}'"
                ) from exc

    def remove_bookshelf(self, location: str, name: str) -> bool:
        with self.engine.begin() as conn:
            shelf_row = conn.execute(
                select(bookshelves_table).where(
                    and_(
                        bookshelves_table.c.location == location,
                        bookshelves_table.c.name == name,
                    )
                )
            ).mappings().one_or_none()

            if shelf_row is None:
                return False

            shelf_id = shelf_row["id"]
            books_on_shelf = conn.execute(
                select(func.count())
                    .select_from(books_table)
                    .where(books_table.c.home_bookshelf_id == shelf_id)
            ).scalar_one()

            if books_on_shelf:
                raise ValueError(
                    f"Cannot remove bookshelf '{name}' - it has {books_on_shelf} books assigned"
                )

            conn.execute(
                bookshelves_table.delete().where(bookshelves_table.c.id == shelf_id)
            )

        return True

    # ------------------------------------------------------------------
    # Book helpers
    # ------------------------------------------------------------------
    def get_books(self) -> Dict[str, BookRecord]:
        stmt = self._book_select().order_by(books_table.c.title)
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()

        return {row["isbn"]: self._row_to_book_record(row) for row in rows}

    def get_book(self, isbn: str) -> Optional[BookRecord]:
        stmt = self._book_select().where(books_table.c.isbn == isbn)
        with self.engine.connect() as conn:
            row = conn.execute(stmt).mappings().one_or_none()

        if row is None:
            return None
        return self._row_to_book_record(row)

    def add_or_update_book(self, book_record: BookRecord) -> None:
        payload = self._book_record_to_row(book_record)
        isbn = book_record.book_info.isbn
        now_iso = utcnow_iso()

        with self.engine.begin() as conn:
            existing = conn.execute(
                select(books_table.c.isbn).where(books_table.c.isbn == isbn)
            ).first()

            if existing:
                payload["updated_at"] = now_iso
                conn.execute(
                    books_table.update()
                    .where(books_table.c.isbn == isbn)
                    .values(**payload)
                )
            else:
                payload.setdefault("created_at", now_iso)
                payload.setdefault("updated_at", now_iso)
                conn.execute(books_table.insert().values(**payload))

    def remove_book(self, isbn: str) -> bool:
        with self.engine.begin() as conn:
            result = conn.execute(
                books_table.delete().where(books_table.c.isbn == isbn)
            )
        return bool(result.rowcount)

    def get_books_on_shelf(
        self,
        location: str,
        bookshelf_name: str,
        column: Optional[int] = None,
        row: Optional[int] = None,
    ) -> List[BookRecord]:
        stmt = self._book_select().where(
            and_(
                bookshelves_table.c.location == location,
                bookshelves_table.c.name == bookshelf_name,
            )
        )

        if column is not None:
            stmt = stmt.where(books_table.c.home_column == column)
        if row is not None:
            stmt = stmt.where(books_table.c.home_row == row)

        stmt = stmt.where(books_table.c.checked_out_to.is_(None))

        with self.engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()

        return [self._row_to_book_record(row) for row in rows]

    def search_books(self, query: str) -> List[BookRecord]:
        query = query.strip()
        if not query:
            return []

        ordered_rows: "OrderedDict[str, RowMapping]" = OrderedDict()
        tokens = _tokenize_query(query)

        with self.engine.connect() as conn:
            if tokens:
                match_expr = " ".join(f"{token}*" for token in tokens)
                fts_sql = text(
                    """
                    SELECT b.*, bs.location AS shelf_location, bs.name AS shelf_name
                    FROM books_fts f
                    JOIN books b ON b.isbn = f.isbn
                    LEFT JOIN bookshelves bs ON bs.id = b.home_bookshelf_id
                    WHERE books_fts MATCH :match
                    ORDER BY bm25(books_fts)
                    LIMIT :limit
                    """
                )

                rows = conn.execute(
                    fts_sql,
                    {"match": match_expr, "limit": SEARCH_LIMIT},
                ).mappings()
                for row in rows:
                    ordered_rows.setdefault(row["isbn"], row)

            like_pattern = f"%{query.lower()}%"
            basic_stmt = (
                self._book_select()
                .where(
                    or_(
                        func.lower(books_table.c.title).like(like_pattern),
                        func.lower(books_table.c.authors).like(like_pattern),
                        func.lower(books_table.c.description).like(like_pattern),
                    )
                )
                .limit(SEARCH_LIMIT)
            )
            for row in conn.execute(basic_stmt).mappings():
                ordered_rows.setdefault(row["isbn"], row)

            clean_isbn = re.sub(r"[^0-9Xx]", "", query)
            if clean_isbn:
                isbn_stmt = (
                    self._book_select()
                    .where(func.replace(func.replace(books_table.c.isbn, "-", ""), " ", "").like(f"%{clean_isbn}%"))
                    .limit(SEARCH_LIMIT)
                )
                for row in conn.execute(isbn_stmt).mappings():
                    ordered_rows.setdefault(row["isbn"], row)

        return [self._row_to_book_record(row) for row in ordered_rows.values()]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _book_select(self) -> Select[Any]:
        return (
            select(
                books_table,
                bookshelves_table.c.location.label("shelf_location"),
                bookshelves_table.c.name.label("shelf_name"),
            )
            .select_from(
                books_table.outerjoin(
                    bookshelves_table,
                    books_table.c.home_bookshelf_id == bookshelves_table.c.id,
                )
            )
        )

    def _row_to_book_record(self, row: RowMapping) -> BookRecord:
        authors = _split_list(row["authors"])
        if not authors:
            authors = ["Unknown Author"]

        genres_list = _split_list(row["genres"])
        book_info = BookInfo(
            isbn=row["isbn"],
            title=row["title"],
            authors=authors,
            publisher=row["publisher"],
            published_date=row["published_date"],
            description=row["description"],
            genres=genres_list or None,
            page_count=row["page_count"],
            cover_url=row["cover_url"],
            language=row["language"],
        )

        home_location: Optional[ShelfLocation] = None
        if (
            row["shelf_location"]
            and row["shelf_name"]
            and row["home_column"] is not None
            and row["home_row"] is not None
        ):
            home_location = ShelfLocation(
                location=row["shelf_location"],
                bookshelf_name=row["shelf_name"],
                column=row["home_column"],
                row=row["home_row"],
            )

        return BookRecord(
            book_info=book_info,
            home_location=home_location,
            checked_out_to=row["checked_out_to"],
            checked_out_date=row["checked_out_date"],
            notes=row["notes"],
        )

    def _book_record_to_row(self, record: BookRecord) -> Dict[str, object]:
        authors = _join_list(record.book_info.authors)
        genres = _join_optional_list(record.book_info.genres)

        payload: Dict[str, object] = {
            "isbn": record.book_info.isbn,
            "title": record.book_info.title,
            "authors": authors,
            "publisher": record.book_info.publisher,
            "published_date": record.book_info.published_date,
            "description": record.book_info.description,
            "genres": genres,
            "page_count": record.book_info.page_count,
            "cover_url": record.book_info.cover_url,
            "language": record.book_info.language,
            "checked_out_to": record.checked_out_to,
            "checked_out_date": record.checked_out_date,
            "notes": record.notes,
        }

        if record.home_location:
            bookshelf_row = self._fetch_bookshelf_row(
                record.home_location.location,
                record.home_location.bookshelf_name,
            )
            if bookshelf_row is None:
                raise ValueError(
                    f"Bookshelf '{record.home_location.bookshelf_name}' not found in '{record.home_location.location}'"
                )

            bookshelf = Bookshelf(
                location=bookshelf_row["location"],
                name=bookshelf_row["name"],
                rows=bookshelf_row["rows"],
                columns=bookshelf_row["columns"],
                description=bookshelf_row["description"],
            )
            bookshelf.get_shelf_location(
                record.home_location.column, record.home_location.row
            )

            payload.update(
                {
                    "home_bookshelf_id": bookshelf_row["id"],
                    "home_column": record.home_location.column,
                    "home_row": record.home_location.row,
                }
            )
        else:
            payload.update(
                {
                    "home_bookshelf_id": None,
                    "home_column": None,
                    "home_row": None,
                }
            )

        return payload

    def _fetch_bookshelf_row(self, location: str, name: str) -> Optional[RowMapping]:
        stmt = select(bookshelves_table).where(
            and_(
                bookshelves_table.c.location == location,
                bookshelves_table.c.name == name,
            )
        )
        with self.engine.connect() as conn:
            return conn.execute(stmt).mappings().one_or_none()

    def _maybe_warn_about_legacy_json(self) -> None:
        if self._legacy_warning_emitted:
            return

        books_json = self.db_path.parent / "books.json"
        shelves_json = self.db_path.parent / "bookshelves.json"

        if books_json.exists() and shelves_json.exists() and self._database_is_empty():
            logger.warning(
                "Legacy JSON data detected in %s. Run scripts/migrate_json_to_sqlite.py --json-dir %s --db-path %s to import your collection.",
                books_json.parent,
                books_json.parent,
                self.db_path,
            )
            self._legacy_warning_emitted = True

    def _database_is_empty(self) -> bool:
        with self.engine.connect() as conn:
            count = conn.execute(
                select(func.count()).select_from(books_table)
            ).scalar_one()
        return count == 0