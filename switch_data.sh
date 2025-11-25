#!/bin/bash
# Script to switch between production and test SQLite databases for Bookwyrm's Hoard

set -euo pipefail

DATA_DIR="data"
ACTIVE_DB="$DATA_DIR/books.db"
TEST_DB="$DATA_DIR/books_test.db"
PROD_DB="$DATA_DIR/books_production.db"

backup_active_db() {
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    cp "$ACTIVE_DB" "$DATA_DIR/books_backup_${timestamp}.db"
    echo "💾 Backup saved to $DATA_DIR/books_backup_${timestamp}.db"
}

require_db() {
    local file="$1"
    local label="$2"
    if [ ! -f "$file" ]; then
        echo "❌ $label database not found at $file"
        echo "   Use: python scripts/migrate_json_to_sqlite.py --json-dir data --db-path $file --force"
        exit 1
    fi
}

copy_db() {
    local source="$1"
    local destination="$2"
    cp "$source" "$destination"
}

pretty_counts() {
    if [ ! -f "$ACTIVE_DB" ]; then
        echo "   Books: unknown"
        echo "   Shelves: unknown"
        return
    fi

    if command -v sqlite3 >/dev/null 2>&1; then
        local books shelves
        books=$(sqlite3 "$ACTIVE_DB" "SELECT COUNT(*) FROM books;" 2>/dev/null || echo "unknown")
        shelves=$(sqlite3 "$ACTIVE_DB" "SELECT COUNT(*) FROM bookshelves;" 2>/dev/null || echo "unknown")
        echo "   Books: $books entries"
        echo "   Shelves: $shelves entries"
    else
        echo "   (Install sqlite3 CLI to show counts)"
    fi
}

case "$1" in
    "test")
        echo "🧪 Switching to TEST database..."
        require_db "$TEST_DB" "Test"
        [ -f "$ACTIVE_DB" ] && backup_active_db
        copy_db "$TEST_DB" "$ACTIVE_DB"
        echo "✅ Test database activated"
        ;;
    "production" | "prod")
        echo "🏭 Switching to PRODUCTION database..."
        require_db "$PROD_DB" "Production"
        [ -f "$ACTIVE_DB" ] && backup_active_db
        copy_db "$PROD_DB" "$ACTIVE_DB"
        echo "✅ Production database activated"
        ;;
    "backup")
        if [ -f "$ACTIVE_DB" ]; then
            backup_active_db
        else
            echo "⚠️  No active database at $ACTIVE_DB"
        fi
        ;;
    "status")
        echo "📊 Current data status:"
        if [ -f "$ACTIVE_DB" ] && [ -f "$TEST_DB" ] && cmp -s "$ACTIVE_DB" "$TEST_DB"; then
            echo "   Currently using: TEST database 🧪"
        elif [ -f "$ACTIVE_DB" ] && [ -f "$PROD_DB" ] && cmp -s "$ACTIVE_DB" "$PROD_DB"; then
            echo "   Currently using: PRODUCTION database 🏭"
        elif [ -f "$ACTIVE_DB" ]; then
            echo "   Currently using: CUSTOM/MODIFIED database ⚠️"
        else
            echo "   No active database found"
        fi
        pretty_counts
        ;;
    *)
        echo "📚 Bookwyrm's Hoard Data Switcher"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  test        Switch to test database (safe dataset)"
        echo "  production  Switch to production database"
        echo "  prod        Alias for production"
        echo "  backup      Create timestamped backup of current DB"
        echo "  status      Show which DB is currently active"
        echo ""
        echo "To create the test/production databases from existing JSON backups, run:"
        echo "  python scripts/migrate_json_to_sqlite.py --json-dir data --db-path $TEST_DB --force"
        echo "  python scripts/migrate_json_to_sqlite.py --json-dir data --db-path $PROD_DB --force"
        ;;
esac