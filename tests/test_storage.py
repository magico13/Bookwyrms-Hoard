"""Unit tests for the SQLite-backed BookshelfStorage."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bookwyrms.models import BookInfo
from bookwyrms.shelf_models import BookRecord, Bookshelf
from bookwyrms.storage import BookshelfStorage


class BookshelfStorageTests(unittest.TestCase):
    """Exercise the primary storage flows against an ephemeral SQLite DB."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test.db"
        self.storage = BookshelfStorage(db_path=self.db_path)

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_add_and_fetch_book(self) -> None:
        shelf = Bookshelf(location="Library", name="Test Shelf", rows=2, columns=2)
        self.storage.add_bookshelf(shelf)

        book_info = BookInfo(
            isbn="TEST-ISBN",
            title="Test Driven Development",
            authors=["Kent Beck"],
            published_date="2002",
        )
        location = shelf.get_shelf_location(0, 0)
        record = BookRecord(book_info=book_info, home_location=location)
        self.storage.add_or_update_book(record)

        # Direct fetch
        stored = self.storage.get_book("TEST-ISBN")
        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertEqual(stored.book_info.title, "Test Driven Development")
        self.assertEqual(stored.home_location, location)

        # Shelf query ignores checked-out items
        on_shelf = self.storage.get_books_on_shelf("Library", "Test Shelf")
        self.assertEqual(len(on_shelf), 1)
        self.assertEqual(on_shelf[0].book_info.isbn, "TEST-ISBN")

    def test_search_ranks_multi_term_queries(self) -> None:
        shelf = Bookshelf(location="Library", name="Sci-Fi", rows=2, columns=2)
        self.storage.add_bookshelf(shelf)
        location = shelf.get_shelf_location(0, 0)

        matches = [
            ("9780000000001", "Fourth Consort", ["Edward Ashton"], "Fourth book"),
            ("9780000000002", "Third Consort", ["Edward Ashton"], "Third book"),
            ("9780000000003", "Random Title", ["Some Author"], "Unrelated"),
        ]

        for isbn_value, title, authors, desc in matches:
            info = BookInfo(
                isbn=isbn_value,
                title=title,
                authors=authors,
                description=desc,
            )
            record = BookRecord(book_info=info, home_location=location)
            self.storage.add_or_update_book(record)

        results = self.storage.search_books("Edward Ashton Fourth Consort")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].book_info.title, "Fourth Consort")

        # ISBN partial search still returns matches
        isbn_results = self.storage.search_books("978000000000")
        self.assertTrue(any(r.book_info.title == "Fourth Consort" for r in isbn_results))


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    unittest.main()
