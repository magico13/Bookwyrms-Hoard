"""Migrate legacy JSON data files into the SQLite database."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Optional

from bookwyrms.storage import BookshelfStorage
from bookwyrms.storage_json import JSONBookshelfStorage


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy data from books.json/bookshelves.json into the SQLite DB."
    )
    parser.add_argument(
        "--json-dir",
        default="data",
        help="Directory containing books.json and bookshelves.json (default: data)",
    )
    parser.add_argument(
        "--db-path",
        default="data/books.db",
        help="Destination SQLite database path (default: data/books.db)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing SQLite file (a backup will be created unless --no-backup)",
    )
    parser.add_argument(
        "--backup",
        default=None,
        help="Optional path to store a backup of an existing SQLite file before overwrite",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without writing to SQLite",
    )
    return parser.parse_args()


def ensure_backup(db_path: Path, backup_path: Optional[Path]) -> None:
    if not db_path.exists():
        return

    if not backup_path:
        backup_path = db_path.with_suffix(db_path.suffix + ".bak")

    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(db_path, backup_path)
    print(f"💾 Backup of existing DB saved to {backup_path}")
    db_path.unlink()


def main() -> None:
    args = parse_args()
    json_dir = Path(args.json_dir)
    db_path = Path(args.db_path)

    json_storage = JSONBookshelfStorage(json_dir)
    shelves = json_storage.get_bookshelves()
    books = json_storage.get_books()

    if args.dry_run:
        print("ℹ️  Dry run only")
        print(f"   Bookshelves to migrate: {len(shelves)}")
        print(f"   Books to migrate: {len(books)}")
        return

    if db_path.exists() and not args.force:
        print(
            f"❌ {db_path} already exists. Re-run with --force to overwrite or --dry-run to inspect.",
            file=sys.stderr,
        )
        sys.exit(1)

    ensure_backup(db_path, Path(args.backup).expanduser() if args.backup else None)

    sqlite_storage = BookshelfStorage(db_path=db_path)

    # Insert shelves in deterministic order
    for shelf in sorted(shelves.values(), key=lambda s: (s.location, s.name)):
        sqlite_storage.add_bookshelf(shelf)

    for book in books.values():
        sqlite_storage.add_or_update_book(book)

    print("✅ Migration complete")
    print(f"   Bookshelves migrated: {len(shelves)}")
    print(f"   Books migrated: {len(books)}")
    print(f"   SQLite file: {db_path}")


if __name__ == "__main__":  # pragma: no cover - script entrypoint
    main()
