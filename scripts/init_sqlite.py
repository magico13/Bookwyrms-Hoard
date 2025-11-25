"""Initialize the SQLite database used by Bookwyrm's Hoard."""

from __future__ import annotations

import argparse
from pathlib import Path

from bookwyrms.db import create_sqlite_engine, initialize_database


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create an empty SQLite database for Bookwyrm's Hoard."
    )
    parser.add_argument(
        "--db-path",
        default="data/books.db",
        help="Path to the SQLite database file (default: data/books.db)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_path = Path(args.db_path).expanduser()

    engine = create_sqlite_engine(db_path)
    initialize_database(engine)
    print(f"✅ SQLite database ready at {db_path}")


if __name__ == "__main__":  # pragma: no cover - script entrypoint
    main()
