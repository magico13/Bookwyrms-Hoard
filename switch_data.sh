#!/bin/bash
# Script to switch between production and test data for Bookwyrms-Hoard

DATA_DIR="data"

case "$1" in
    "test")
        echo "🧪 Switching to TEST data..."
        if [ -f "$DATA_DIR/books_test.json" ] && [ -f "$DATA_DIR/bookshelves_test.json" ]; then
            # Backup current active data
            cp "$DATA_DIR/books.json" "$DATA_DIR/books_backup.json" 2>/dev/null || true
            cp "$DATA_DIR/bookshelves.json" "$DATA_DIR/bookshelves_backup.json" 2>/dev/null || true
            
            # Switch to test data
            cp "$DATA_DIR/books_test.json" "$DATA_DIR/books.json"
            cp "$DATA_DIR/bookshelves_test.json" "$DATA_DIR/bookshelves.json"
            
            echo "✅ Switched to test data"
            echo "📚 Test dataset:"
            echo "   - 5 test books with predictable ISBNs"
            echo "   - 2 test bookshelves (Library/Test Shelf, Office/Small Shelf)"
            echo "   - 1 pre-checked-out book for testing error scenarios"
            echo ""
            echo "📋 Test ISBNs you can use:"
            echo "   - 9780134685991 (Effective Python)"
            echo "   - 9780262046305 (Introduction to Algorithms)"
            echo "   - 9781491950296 (Programming Rust)"
            echo "   - TEST123456789 (The Art of Testing APIs)"
            echo "   - CHECKED456789 (Pre-checked out book)"
        else
            echo "❌ Test data files not found!"
            exit 1
        fi
        ;;
    "production" | "prod")
        echo "🏭 Switching to PRODUCTION data..."
        if [ -f "$DATA_DIR/books_production.json" ] && [ -f "$DATA_DIR/bookshelves_production.json" ]; then
            # Backup current active data
            cp "$DATA_DIR/books.json" "$DATA_DIR/books_backup.json" 2>/dev/null || true
            cp "$DATA_DIR/bookshelves.json" "$DATA_DIR/bookshelves_backup.json" 2>/dev/null || true
            
            # Switch to production data
            cp "$DATA_DIR/books_production.json" "$DATA_DIR/books.json"
            cp "$DATA_DIR/bookshelves_production.json" "$DATA_DIR/bookshelves.json"
            
            echo "✅ Switched to production data"
            echo "📚 Your full library collection is now active"
        else
            echo "❌ Production backup files not found!"
            exit 1
        fi
        ;;
    "backup")
        echo "💾 Creating backup of current active data..."
        cp "$DATA_DIR/books.json" "$DATA_DIR/books_backup_$(date +%Y%m%d_%H%M%S).json"
        cp "$DATA_DIR/bookshelves.json" "$DATA_DIR/bookshelves_backup_$(date +%Y%m%d_%H%M%S).json"
        echo "✅ Backup created with timestamp"
        ;;
    "status")
        echo "📊 Current data status:"
        if cmp -s "$DATA_DIR/books.json" "$DATA_DIR/books_test.json" 2>/dev/null; then
            echo "   Currently using: TEST data 🧪"
        elif cmp -s "$DATA_DIR/books.json" "$DATA_DIR/books_production.json" 2>/dev/null; then
            echo "   Currently using: PRODUCTION data 🏭"
        else
            echo "   Currently using: UNKNOWN/MODIFIED data ⚠️"
        fi
        echo "   Books: $(jq 'length' "$DATA_DIR/books.json" 2>/dev/null || echo "unknown") entries"
        echo "   Shelves: $(jq 'length' "$DATA_DIR/bookshelves.json" 2>/dev/null || echo "unknown") entries"
        ;;
    *)
        echo "📚 Bookwyrms-Hoard Data Switcher"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  test        Switch to test data (safe for API testing)"
        echo "  production  Switch to production data (your real library)"
        echo "  prod        Alias for production"
        echo "  backup      Create timestamped backup of current data"
        echo "  status      Show which dataset is currently active"
        echo ""
        echo "Files:"
        echo "  books.json / bookshelves.json       - Active data"
        echo "  books_test.json / bookshelves_test.json - Test dataset"
        echo "  books_production.json / bookshelves_production.json - Production backup"
        ;;
esac