/**
 * API client for Bookwyrm's Hoard
 */

class API {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        const config = { ...defaultOptions, ...options };
        
        if (config.body && typeof config.body === 'object') {
            config.body = JSON.stringify(config.body);
        }

        try {
            console.log(`API Request: ${config.method || 'GET'} ${url}`);
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            console.log(`API Response: ${url}`, data);
            return data;
        } catch (error) {
            console.error(`API Error: ${url}`, error);
            throw error;
        }
    }

    // Book operations
    async getBookByISBN(isbn) {
        return this.request(`/api/books/${encodeURIComponent(isbn)}`);
    }

    async lookupBookByISBN(isbn) {
        return this.request(`/api/lookup/${encodeURIComponent(isbn)}`);
    }

    async searchBooks(query) {
        const params = new URLSearchParams();
        // Use the new smart search endpoint
        if (query) {
            params.append('q', query);
        }
        
        const url = `/api/books?${params.toString()}`;
        console.log('Search URL:', url);
        return this.request(url);
    }

    async addBook(bookData) {
        return this.request('/api/books', {
            method: 'POST',
            body: bookData
        });
    }

    async checkoutBook(isbn, checkedOutTo) {
        return this.request(`/api/books/${encodeURIComponent(isbn)}/checkout`, {
            method: 'POST',
            body: { checked_out_to: checkedOutTo }
        });
    }

    async checkinBook(isbn, location = null) {
        const body = {};
        if (location) {
            body.location = location.location;
            body.bookshelf_name = location.bookshelf_name;
            body.column = location.column;
            body.row = location.row;
        }

        return this.request(`/api/books/${encodeURIComponent(isbn)}/checkin`, {
            method: 'POST',
            body: Object.keys(body).length > 0 ? body : null
        });
    }

    // Shelf operations
    async getShelves() {
        return this.request('/api/shelves');
    }

    async createShelf(shelfData) {
        return this.request('/api/shelves', {
            method: 'POST',
            body: shelfData
        });
    }

    // Health check
    async healthCheck() {
        return this.request('/api/health');
    }
}

// Create global API instance
window.api = new API();