/**
 * Kiosk application for Bookwyrm's Hoard
 * Optimized for 800x480 touchscreen with barcode scanner
 */

class KioskApp {
    constructor() {
        this.currentBook = null;
        this.currentScreen = 'search';
        this.shelves = [];
        this.selectedLocation = null;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadShelves();
        this.showScreen('search');
        this.focusSearchInput();
    }

    setupEventListeners() {
        // Search screen
        document.getElementById('search-btn').addEventListener('click', () => this.handleSearch());
        document.getElementById('search-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.handleSearch();
        });

        // No more search mode toggle needed

        // Navigation buttons
        document.getElementById('back-btn').addEventListener('click', () => this.goToSearch());
        document.getElementById('results-back-btn').addEventListener('click', () => this.goToSearch());

        // Checkout flow
        document.getElementById('confirm-checkout-btn').addEventListener('click', () => this.confirmCheckout());
        document.getElementById('cancel-checkout-btn').addEventListener('click', () => this.showBookScreen());
        
        // Add enter key handler for checkout name input
        document.getElementById('checkout-name').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.confirmCheckout();
        });

        // Checkin flow
        document.getElementById('return-home-btn').addEventListener('click', () => this.returnToHome());
        document.getElementById('different-location-btn').addEventListener('click', () => this.showLocationPicker('checkin'));
        document.getElementById('cancel-checkin-btn').addEventListener('click', () => this.showBookScreen());

        // Location picker
        document.getElementById('room-select').addEventListener('change', () => this.updateShelfOptions());
        document.getElementById('shelf-select').addEventListener('change', () => this.showShelfGrid());
        document.getElementById('confirm-location-btn').addEventListener('click', () => this.confirmLocation());
        document.getElementById('cancel-location-btn').addEventListener('click', () => this.showBookScreen());

        // Modals
        document.getElementById('error-ok-btn').addEventListener('click', () => this.hideModal('error-modal'));
        document.getElementById('success-ok-btn').addEventListener('click', () => this.hideModal('success-modal'));

        // Auto-focus search input when returning to search screen
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && this.currentScreen === 'search') {
                this.focusSearchInput();
            }
        });
    }

    isISBN(query) {
        // Remove hyphens and spaces
        const cleaned = query.replace(/[-\s]/g, '');
        
        // Check if it's all digits and is 10 or 13 characters
        return /^\d{10}$/.test(cleaned) || /^\d{13}$/.test(cleaned);
    }

    focusSearchInput() {
        setTimeout(() => {
            const searchInput = document.getElementById('search-input');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }, 100);
    }

    showScreen(screenName) {
        // Hide all screens
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.remove('active');
        });

        // Show target screen
        const targetScreen = document.getElementById(`${screenName}-screen`);
        if (targetScreen) {
            targetScreen.classList.add('active');
            this.currentScreen = screenName;
        }

        // Screen-specific setup
        if (screenName === 'search') {
            this.clearSearchInput();
            this.focusSearchInput();
        } else if (screenName === 'checkout') {
            this.updateCheckoutBookInfo();
            setTimeout(() => {
                const nameInput = document.getElementById('checkout-name');
                if (nameInput) nameInput.focus();
            }, 100);
        } else if (screenName === 'checkin') {
            this.updateCheckinBookInfo();
        }
    }

    updateCheckoutBookInfo() {
        if (!this.currentBook) return;
        
        const bookInfoElement = document.getElementById('checkout-book-info');
        const bookInfo = this.currentBook.book_info;
        
        // Handle author display properly
        let authorDisplay = 'Unknown Author';
        if (bookInfo.author && bookInfo.author !== 'undefined') {
            authorDisplay = bookInfo.author;
        } else if (bookInfo.authors && bookInfo.authors.length > 0) {
            authorDisplay = bookInfo.authors.join(', ');
        }

        bookInfoElement.innerHTML = `
            <div style="text-align: center;">
                <h3>${bookInfo.title || 'Unknown Title'}</h3>
                <div class="text-muted">${authorDisplay}</div>
                <div class="text-muted">ISBN: ${bookInfo.isbn || 'N/A'}</div>
            </div>
        `;
    }

    updateCheckinBookInfo() {
        if (!this.currentBook) return;
        
        const bookInfoElement = document.getElementById('checkin-book-info');
        const bookInfo = this.currentBook.book_info;
        
        let statusText = 'On shelf';
        if (this.currentBook.checked_out_to) {
            statusText = `Checked out to ${this.currentBook.checked_out_to}`;
        }
        
        // Handle author display properly
        let authorDisplay = 'Unknown Author';
        if (bookInfo.author && bookInfo.author !== 'undefined') {
            authorDisplay = bookInfo.author;
        } else if (bookInfo.authors && bookInfo.authors.length > 0) {
            authorDisplay = bookInfo.authors.join(', ');
        }

        bookInfoElement.innerHTML = `
            <div style="text-align: center;">
                <h3>${bookInfo.title || 'Unknown Title'}</h3>
                <div class="text-muted">${authorDisplay}</div>
                <div class="text-muted">ISBN: ${bookInfo.isbn || 'N/A'}</div>
                <div style="margin-top: 10px;"><strong>Status:</strong> ${statusText}</div>
            </div>
        `;
    }

    clearSearchInput() {
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.value = '';
        }
    }

    showLoading(show = true) {
        const loading = document.getElementById('loading');
        if (show) {
            loading.classList.add('active');
        } else {
            loading.classList.remove('active');
        }
    }

    showModal(modalId, title, message) {
        const modal = document.getElementById(modalId);
        const messageElement = document.getElementById(modalId.replace('-modal', '-message'));
        
        if (messageElement) {
            messageElement.textContent = message;
        }
        
        modal.classList.add('active');
    }

    hideModal(modalId) {
        document.getElementById(modalId).classList.remove('active');
        
        // Return focus to search if we're done with an operation
        if (this.currentScreen === 'search') {
            this.focusSearchInput();
        }
    }

    async handleSearch() {
        const searchInput = document.getElementById('search-input');
        const query = searchInput.value.trim();
        
        if (!query) {
            this.showModal('error-modal', 'Error', 'Please enter something to search for.');
            return;
        }

        this.showLoading();
        
        try {
            if (this.isISBN(query)) {
                console.log('Detected ISBN search:', query);
                await this.searchByISBN(query);
            } else {
                console.log('Detected text search:', query);
                await this.searchByText(query);
            }
        } catch (error) {
            console.error('Search error:', error);
            this.showModal('error-modal', 'Search Error', error.message);
        } finally {
            this.showLoading(false);
        }
    }

    async searchByISBN(isbn) {
        console.log('Searching for ISBN:', isbn);
        try {
            // First try to find the book in our library
            const bookData = await api.getBookByISBN(isbn);
            console.log('Found book in library:', bookData);
            this.currentBook = bookData;
            this.showBookScreen();
        } catch (error) {
            console.log('Book not in library, error:', error.message);
            if (error.message.includes('404') || error.message.includes('not found')) {
                // Book not in library, try external lookup
                try {
                    console.log('Trying external lookup...');
                    const lookupData = await api.lookupBookByISBN(isbn);
                    console.log('External lookup result:', lookupData);
                    this.currentBook = {
                        book_info: lookupData.book_info,
                        status: 'new'
                    };
                    this.showBookScreen();
                } catch (lookupError) {
                    console.log('External lookup failed:', lookupError.message);
                    throw new Error(`Book not found in library or external sources: ${lookupError.message}`);
                }
            } else {
                throw error;
            }
        }
    }

    async searchByText(query) {
        console.log('Searching by text:', query);
        try {
            const results = await api.searchBooks(query);
            console.log('Search results:', results);
            
            // API returns array directly
            if (!results || results.length === 0) {
                this.showModal('error-modal', 'No Results', 'No books found matching your search.');
                return;
            }

            if (results.length === 1) {
                // Only one result, show it directly
                this.currentBook = results[0];
                this.showBookScreen();
            } else {
                // Multiple results - show results list
                this.showResultsList(results, query);
            }
        } catch (error) {
            console.error('Text search error:', error);
            throw error;
        }
    }

    showBookScreen() {
        if (!this.currentBook) return;

        const bookInfo = this.currentBook.book_info;
        const isNewBook = this.currentBook.status === 'new';
        
        // Update book info display
        this.updateBookInfoDisplay(bookInfo);
        
        // Update actions based on book status
        this.updateBookActions(isNewBook);
        
        // Update shelf display
        this.updateShelfDisplay();
        
        this.showScreen('book');
    }

    updateBookInfoDisplay(bookInfo) {
        const bookInfoElement = document.getElementById('book-info');
        
        let statusHtml = '';
        if (this.currentBook.status === 'new') {
            statusHtml = '<div class="book-status status-available"><strong>NEW BOOK</strong><br>Not yet in library</div>';
        } else if (this.currentBook.checked_out_to) {
            statusHtml = `<div class="book-status status-checked-out"><strong>CHECKED OUT</strong><br>to ${this.currentBook.checked_out_to}</div>`;
        } else {
            statusHtml = '<div class="book-status status-available"><strong>AVAILABLE</strong><br>On shelf</div>';
        }

        // Handle author display properly for minimal lookup data
        let authorDisplay = 'Unknown Author';
        if (bookInfo.author && bookInfo.author !== 'undefined') {
            authorDisplay = bookInfo.author;
        } else if (bookInfo.authors && bookInfo.authors.length > 0) {
            authorDisplay = bookInfo.authors.join(', ');
        }
        
        bookInfoElement.innerHTML = `
            <div class="book-info">
                <h2>${bookInfo.title || 'Unknown Title'}</h2>
                <div class="author">${authorDisplay}</div>
                <div class="isbn">ISBN: ${bookInfo.isbn || 'N/A'}</div>
                ${statusHtml}
                ${bookInfo.description ? `<div class="description">${bookInfo.description}</div>` : ''}
            </div>
        `;
    }

    updateBookActions(isNewBook) {
        const actionsElement = document.getElementById('book-actions');
        
        if (isNewBook) {
            actionsElement.innerHTML = `
                <button class="btn btn-primary" onclick="kioskApp.showLocationPicker('add')">
                    📚 Add to Library
                </button>
            `;
        } else if (this.currentBook.checked_out_to) {
            // Book is checked out - only allow check in
            actionsElement.innerHTML = `
                <button class="btn btn-success" onclick="kioskApp.showScreen('checkin')">
                    📥 Check In
                </button>
            `;
        } else {
            // Book is available on shelf - only allow check out
            actionsElement.innerHTML = `
                <button class="btn btn-primary" onclick="kioskApp.showScreen('checkout')">
                    📤 Check Out
                </button>
            `;
        }
    }

    updateShelfDisplay() {
        const shelfInfoElement = document.getElementById('shelf-info');
        
        if (this.currentBook.status === 'new' || !this.currentBook.home_location) {
            shelfInfoElement.innerHTML = '<div class="text-muted">No shelf location</div>';
            return;
        }

        const location = this.currentBook.home_location;
        console.log('Looking for shelf:', location);
        console.log('Available shelves:', this.shelves);
        
        const shelf = this.shelves.find(s => 
            s.location === location.location && s.name === location.bookshelf_name
        );

        if (!shelf) {
            shelfInfoElement.innerHTML = `
                <div class="text-muted">
                    Shelf not found<br>
                    <small>Looking for: ${location.location}/${location.bookshelf_name}</small>
                </div>
            `;
            return;
        }

        shelfInfoElement.innerHTML = `
            <h3>${location.location}</h3>
            <div style="margin-bottom: 10px;">${location.bookshelf_name}</div>
            ${this.renderShelfGrid(shelf, location.column, location.row, false)}
        `;
    }

    renderShelfGrid(shelf, homeColumn = null, homeRow = null, clickable = false) {
        const gridStyle = `grid-template-columns: repeat(${shelf.columns}, 1fr); grid-template-rows: repeat(${shelf.rows}, 1fr);`;
        
        let gridHtml = `<div class="shelf-grid" style="${gridStyle}">`;
        
        for (let row = 0; row < shelf.rows; row++) {
            for (let col = 0; col < shelf.columns; col++) {
                const isHome = (col === homeColumn && row === homeRow);
                const isSelected = (this.selectedLocation && 
                    this.selectedLocation.column === col && 
                    this.selectedLocation.row === row);
                
                let cellClass = 'shelf-cell';
                let cellContent = '';  // Empty by default
                
                if (isHome) {
                    cellClass += ' home';
                    cellContent = '📚';  // Book icon for home position
                } else if (isSelected) {
                    cellClass += ' selected';
                    cellContent = '✓';   // Checkmark for selected
                }
                
                const clickHandler = clickable ? `onclick="kioskApp.selectGridCell(${col}, ${row})"` : '';
                
                gridHtml += `<div class="${cellClass}" ${clickHandler}>${cellContent}</div>`;
            }
        }
        
        gridHtml += '</div>';
        return gridHtml;
    }

    showResultsList(results, query) {
        console.log(`Showing ${results.length} results for query: ${query}`);
        
        // Update title
        const titleElement = document.getElementById('results-title');
        titleElement.textContent = `Found ${results.length} books matching "${query}"`;
        
        // Populate results list
        const resultsListElement = document.getElementById('results-list');
        resultsListElement.innerHTML = '';
        
        results.forEach((book, index) => {
            const resultItem = this.createResultItem(book, index);
            resultsListElement.appendChild(resultItem);
        });
        
        this.showScreen('results');
    }

    createResultItem(book, index) {
        const bookInfo = book.book_info;
        const isCheckedOut = !!book.checked_out_to;
        
        const resultDiv = document.createElement('div');
        resultDiv.className = 'result-item';
        resultDiv.onclick = () => this.selectBookFromResults(book);
        
        // Status info
        let statusHtml, locationHtml;
        if (isCheckedOut) {
            statusHtml = '<div class="status-badge checked-out">Checked Out</div>';
            locationHtml = `<div class="location">to ${book.checked_out_to}</div>`;
        } else {
            statusHtml = '<div class="status-badge available">Available</div>';
            if (book.home_location) {
                locationHtml = `<div class="location">${book.home_location.location}/${book.home_location.bookshelf_name}</div>`;
            } else {
                locationHtml = '<div class="location">No location set</div>';
            }
        }
        
        // Handle author display properly
        let authorDisplay = 'Unknown Author';
        if (bookInfo.author && bookInfo.author !== 'undefined') {
            authorDisplay = bookInfo.author;
        } else if (bookInfo.authors && bookInfo.authors.length > 0) {
            authorDisplay = bookInfo.authors.join(', ');
        }
        
        resultDiv.innerHTML = `
            <div class="result-book-info">
                <div class="title">${bookInfo.title || 'Unknown Title'}</div>
                <div class="author">${authorDisplay}</div>
                <div class="isbn">ISBN: ${bookInfo.isbn || 'N/A'}</div>
            </div>
            <div class="result-status">
                ${statusHtml}
                ${locationHtml}
            </div>
        `;
        
        return resultDiv;
    }

    selectBookFromResults(book) {
        console.log('Selected book from results:', book.book_info.title);
        this.currentBook = book;
        this.showBookScreen();
    }

    goToSearch() {
        this.currentBook = null;
        this.selectedLocation = null;
        this.showScreen('search');
    }

    // Checkout flow
    async confirmCheckout() {
        const nameInput = document.getElementById('checkout-name');
        const name = nameInput.value.trim();
        
        if (!name) {
            this.showModal('error-modal', 'Error', 'Please enter a name.');
            return;
        }

        this.showLoading();
        
        try {
            await api.checkoutBook(this.currentBook.book_info.isbn, name);
            this.showModal('success-modal', 'Success!', `Book checked out to ${name}.`);
            
            // Update current book status
            this.currentBook.checked_out_to = name;
            
            setTimeout(() => {
                this.hideModal('success-modal');
                this.goToSearch();
            }, 2000);
        } catch (error) {
            console.error('Checkout error:', error);
            this.showModal('error-modal', 'Checkout Error', error.message);
        } finally {
            this.showLoading(false);
        }
    }

    // Checkin flow
    async returnToHome() {
        this.showLoading();
        
        try {
            await api.checkinBook(this.currentBook.book_info.isbn);
            this.showModal('success-modal', 'Success!', 'Book returned to home location.');
            
            // Update current book status
            delete this.currentBook.checked_out_to;
            
            setTimeout(() => {
                this.hideModal('success-modal');
                this.goToSearch();
            }, 2000);
        } catch (error) {
            console.error('Checkin error:', error);
            this.showModal('error-modal', 'Checkin Error', error.message);
        } finally {
            this.showLoading(false);
        }
    }

    // Location picker
    showLocationPicker(mode) {
        this.locationMode = mode;
        this.selectedLocation = null;
        
        // Update title based on mode
        const title = document.getElementById('location-title');
        if (mode === 'add') {
            title.textContent = 'Choose Home Location for New Book';
        } else if (mode === 'checkin') {
            title.textContent = 'Choose Different Location';
        }

        // Show book info
        this.updateLocationBookInfo();
        
        // Reset selectors
        this.populateLocationSelectors();
        
        this.showScreen('location');
    }

    updateLocationBookInfo() {
        const bookInfoElement = document.getElementById('location-book-info');
        const bookInfo = this.currentBook.book_info;
        
        // Handle author display properly
        let authorDisplay = 'Unknown Author';
        if (bookInfo.author && bookInfo.author !== 'undefined') {
            authorDisplay = bookInfo.author;
        } else if (bookInfo.authors && bookInfo.authors.length > 0) {
            authorDisplay = bookInfo.authors.join(', ');
        }
        
        bookInfoElement.innerHTML = `
            <div style="text-align: center; padding: 15px; background-color: var(--bg-secondary); border-radius: 8px;">
                <strong>${bookInfo.title || 'Unknown Title'}</strong><br>
                <span class="text-muted">${authorDisplay}</span>
            </div>
        `;
    }

    populateLocationSelectors() {
        const roomSelect = document.getElementById('room-select');
        const shelfSelect = document.getElementById('shelf-select');
        
        // Reset
        roomSelect.innerHTML = '<option value="">Select room...</option>';
        shelfSelect.innerHTML = '<option value="">Select shelf...</option>';
        shelfSelect.disabled = true;
        
        // Get unique rooms
        const rooms = [...new Set(this.shelves.map(s => s.location))];
        rooms.forEach(room => {
            const option = document.createElement('option');
            option.value = room;
            option.textContent = room;
            roomSelect.appendChild(option);
        });
        
        this.clearShelfGrid();
    }

    updateShelfOptions() {
        const roomSelect = document.getElementById('room-select');
        const shelfSelect = document.getElementById('shelf-select');
        
        const selectedRoom = roomSelect.value;
        
        shelfSelect.innerHTML = '<option value="">Select shelf...</option>';
        
        if (selectedRoom) {
            const roomShelves = this.shelves.filter(s => s.location === selectedRoom);
            roomShelves.forEach(shelf => {
                const option = document.createElement('option');
                option.value = shelf.name;
                option.textContent = shelf.name;
                shelfSelect.appendChild(option);
            });
            shelfSelect.disabled = false;
        } else {
            shelfSelect.disabled = true;
        }
        
        this.clearShelfGrid();
    }

    showShelfGrid() {
        const roomSelect = document.getElementById('room-select');
        const shelfSelect = document.getElementById('shelf-select');
        
        const selectedRoom = roomSelect.value;
        const selectedShelfName = shelfSelect.value;
        
        if (!selectedRoom || !selectedShelfName) {
            this.clearShelfGrid();
            return;
        }

        const shelf = this.shelves.find(s => 
            s.location === selectedRoom && s.name === selectedShelfName
        );
        
        if (!shelf) {
            this.clearShelfGrid();
            return;
        }

        this.currentShelf = shelf;
        this.selectedLocation = null;
        
        const gridContainer = document.getElementById('shelf-grid-container');
        gridContainer.innerHTML = `
            <div style="margin-bottom: 15px; text-align: center;">
                <strong>Click a position for the book:</strong>
            </div>
            ${this.renderShelfGrid(shelf, null, null, true)}
        `;
        
        document.getElementById('confirm-location-btn').disabled = true;
    }

    clearShelfGrid() {
        document.getElementById('shelf-grid-container').innerHTML = '';
        document.getElementById('confirm-location-btn').disabled = true;
        this.selectedLocation = null;
    }

    selectGridCell(column, row) {
        this.selectedLocation = {
            location: this.currentShelf.location,
            bookshelf_name: this.currentShelf.name,
            column: column,
            row: row
        };
        
        // Re-render grid with selection
        const gridContainer = document.getElementById('shelf-grid-container');
        gridContainer.innerHTML = `
            <div style="margin-bottom: 15px; text-align: center;">
                <strong>Selected: Column ${column + 1}, Row ${row + 1}</strong>
            </div>
            ${this.renderShelfGrid(this.currentShelf, null, null, true)}
        `;
        
        document.getElementById('confirm-location-btn').disabled = false;
    }

    async confirmLocation() {
        if (!this.selectedLocation) return;

        this.showLoading();
        
        try {
            if (this.locationMode === 'add') {
                // Add new book to library - flatten the book_info structure
                const bookInfo = this.currentBook.book_info;
                const bookData = {
                    isbn: bookInfo.isbn,
                    title: bookInfo.title,
                    authors: bookInfo.authors,
                    publisher: bookInfo.publisher,
                    published_date: bookInfo.published_date,
                    description: bookInfo.description,
                    location: this.selectedLocation.location,
                    bookshelf_name: this.selectedLocation.bookshelf_name,
                    column: this.selectedLocation.column,
                    row: this.selectedLocation.row
                };
                
                await api.addBook(bookData);
                this.showModal('success-modal', 'Success!', 'Book added to library!');
            } else if (this.locationMode === 'checkin') {
                // Check in to different location
                await api.checkinBook(this.currentBook.book_info.isbn, this.selectedLocation);
                this.showModal('success-modal', 'Success!', 'Book checked in to new location!');
                
                // Update current book status
                delete this.currentBook.checked_out_to;
                this.currentBook.home_location = this.selectedLocation;
            }
            
            setTimeout(() => {
                this.hideModal('success-modal');
                this.goToSearch();
            }, 2000);
        } catch (error) {
            console.error('Location confirmation error:', error);
            this.showModal('error-modal', 'Error', error.message);
        } finally {
            this.showLoading(false);
        }
    }

    async loadShelves() {
        try {
            const response = await api.getShelves();
            console.log('Raw shelves response:', response);
            
            // The API returns an array of shelves directly
            if (Array.isArray(response)) {
                this.shelves = response;
            } else if (response.shelves) {
                this.shelves = Array.isArray(response.shelves) ? response.shelves : Object.values(response.shelves);
            } else {
                this.shelves = [];
            }
            console.log('Processed shelves:', this.shelves);
        } catch (error) {
            console.error('Failed to load shelves:', error);
            this.shelves = [];
        }
    }
}

// Initialize the app when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.kioskApp = new KioskApp();
});