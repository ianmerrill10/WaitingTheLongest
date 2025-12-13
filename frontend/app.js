/**
 * ============================================================================
 * Waiting The Longest™ - Frontend Application
 * ============================================================================
 * "Because Every Day Matters"
 * 
 * This is the main JavaScript application for the Waiting The Longest platform.
 * It handles:
 * - Fetching and displaying animals from the API
 * - Filtering and sorting functionality
 * - Animal detail views
 * - Affiliate product recommendations
 * - Success stories display
 * 
 * Author: Waiting The Longest™ Development Team
 * ============================================================================
 */

// =============================================================================
// CONFIGURATION
// =============================================================================

function resolveApiBaseUrl() {
    const fromGlobal =
        (window.WTL_CONFIG && window.WTL_CONFIG.API_BASE_URL) ||
        window.WTL_API_BASE_URL ||
        window.__WTL_API_BASE_URL__;

    const meta = document.querySelector('meta[name="wtl-api-base-url"]');
    const fromMeta = meta ? meta.getAttribute('content') : null;

    const raw = (fromGlobal || fromMeta || window.location.origin || '').trim();
    return raw.replace(/\/+$/, '');
}

const CONFIG = {
    API_BASE_URL: resolveApiBaseUrl(),
    DEFAULT_PAGE_SIZE: 20,
    AFFILIATE_TAG: 'waitingthelon-20',
    CACHE_TTL: 5 * 60 * 1000, // 5 minutes
};

// =============================================================================
// STATE MANAGEMENT
// =============================================================================

const state = {
    animals: [],
    currentAnimal: null,
    filters: {
        species: '',
        breed: '',
        ageGroup: '',
        size: '',
        gender: '',
        state: '',
    },
    sortBy: 'days_waiting',
    sortOrder: 'desc',
    page: 1,
    pageSize: CONFIG.DEFAULT_PAGE_SIZE,
    totalPages: 0,
    totalAnimals: 0,
    isLoading: false,
    error: null,
    successStories: [],
    stats: null,
};

// Simple cache
const cache = new Map();

// =============================================================================
// API CLIENT
// =============================================================================

const api = {
    /**
     * Make API request with error handling
     */
    async request(endpoint, options = {}) {
        const cacheKey = `${endpoint}${JSON.stringify(options)}`;
        
        // Check cache
        const cached = cache.get(cacheKey);
        if (cached && Date.now() - cached.timestamp < CONFIG.CACHE_TTL) {
            return cached.data;
        }
        
        try {
            const response = await fetch(`${CONFIG.API_BASE_URL}${endpoint}`, {
                headers: {
                    'Content-Type': 'application/json',
                },
                ...options,
            });
            
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Cache successful responses
            cache.set(cacheKey, { data, timestamp: Date.now() });
            
            return data;
        } catch (error) {
            // Improved error handling with user-friendly messages
            let userMessage = 'Unable to connect to the server.';
            if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
                userMessage = 'Network error. Please check your internet connection.';
            } else if (error.message.includes('CORS')) {
                userMessage = 'Cross-origin request blocked. The backend may not be configured for this domain.';
            } else if (error.message.includes('API error: 5')) {
                userMessage = 'Server error. Please try again later.';
            }
            console.error('API request failed:', error, '| User message:', userMessage);
            error.userMessage = userMessage;
            throw error;
        }
    },
    
    /**
     * Get paginated list of animals
     */
    async getAnimals(params = {}) {
        const queryParams = new URLSearchParams();
        
        if (params.species) queryParams.set('species', params.species);
        if (params.breed) queryParams.set('breed', params.breed);
        if (params.ageGroup) queryParams.set('age_group', params.ageGroup);
        if (params.size) queryParams.set('size', params.size);
        if (params.gender) queryParams.set('gender', params.gender);
        if (params.state) queryParams.set('state', params.state);
        if (params.sortBy) queryParams.set('sort_by', params.sortBy);
        if (params.sortOrder) queryParams.set('sort_order', params.sortOrder);
        if (params.page) queryParams.set('page', params.page);
        if (params.pageSize) queryParams.set('page_size', params.pageSize);
        
        return this.request(`/api/animals?${queryParams.toString()}`);
    },
    
    /**
     * Get single animal detail
     */
    async getAnimal(id) {
        return this.request(`/api/animals/${id}`);
    },
    
    /**
     * Get longest waiting animals
     */
    async getLongestWaiting(species = null, limit = 10) {
        const params = new URLSearchParams({ limit });
        if (species) params.set('species', species);
        return this.request(`/api/longest-waiting?${params.toString()}`);
    },
    
    /**
     * Get success stories
     */
    async getSuccessStories(limit = 10) {
        return this.request(`/api/success-stories?limit=${limit}`);
    },
    
    /**
     * Submit a success story
     */
    async submitSuccessStory(story) {
        return this.request('/api/success-stories', {
            method: 'POST',
            body: JSON.stringify(story),
        });
    },
    
    /**
     * Get platform stats
     */
    async getStats() {
        return this.request('/api/stats');
    },
    
    /**
     * Get product recommendations
     */
    async getProductRecommendations(petType, petAge = null, petSize = null, limit = 5) {
        const params = new URLSearchParams({ pet_type: petType, limit });
        if (petAge) params.set('pet_age', petAge);
        if (petSize) params.set('pet_size', petSize);
        return this.request(`/api/products/recommendations?${params.toString()}`);
    },
    
    /**
     * Track affiliate click
     */
    async trackAffiliateClick(productId, sourcePage, animalId = null) {
        const params = new URLSearchParams({
            product_id: productId,
            source_page: sourcePage,
        });
        if (animalId) params.set('animal_id', animalId);
        
        return this.request(`/api/affiliate/click?${params.toString()}`, {
            method: 'POST',
        });
    },
    
    /**
     * Health check
     */
    async healthCheck() {
        return this.request('/health');
    },
};

// =============================================================================
// UI COMPONENTS
// =============================================================================

const ui = {
    /**
     * Create an animal card element
     */
    createAnimalCard(animal) {
        const card = document.createElement('div');
        card.className = 'animal-card';
        card.setAttribute('data-animal-id', animal.id);
        card.setAttribute('role', 'article');
        card.setAttribute('aria-label', `${animal.canonical_name}, ${animal.breed_primary}, waiting ${animal.days_waiting} days`);
        
        const photoUrl = animal.photo_url || '/assets/placeholder-dog.jpg';
        const daysWaiting = animal.days_waiting || 0;
        const urgencyClass = daysWaiting > 365 ? 'urgent' : daysWaiting > 180 ? 'warning' : '';
        
        card.innerHTML = `
            <div class="animal-photo">
                <img src="${photoUrl}" 
                     alt="Photo of ${animal.canonical_name}, a ${animal.breed_primary}" 
                     loading="lazy"
                     onerror="this.src='/assets/placeholder-dog.jpg'">
                <span class="days-badge ${urgencyClass}" aria-label="${daysWaiting} days waiting">
                    ${daysWaiting} days
                </span>
            </div>
            <div class="animal-info">
                <h3 class="animal-name">${animal.canonical_name || 'Unknown'}</h3>
                <p class="animal-breed">${animal.breed_primary || 'Mixed Breed'}</p>
                <div class="animal-details">
                    <span class="detail-item">
                        <span class="icon">📍</span>
                        ${animal.city || ''}, ${animal.state || 'Unknown'}
                    </span>
                    <span class="detail-item">
                        <span class="icon">${animal.gender === 'male' ? '♂️' : '♀️'}</span>
                        ${animal.gender || 'Unknown'}
                    </span>
                    <span class="detail-item">
                        <span class="icon">📏</span>
                        ${animal.size || 'Unknown'} • ${animal.age_group || 'Unknown'}
                    </span>
                </div>
            </div>
            <button class="adopt-button" 
                    onclick="app.viewAnimal(${animal.id})"
                    aria-label="Learn more about ${animal.canonical_name}">
                Meet ${animal.canonical_name || 'Me'} 💕
            </button>
        `;
        
        return card;
    },
    
    /**
     * Create a product recommendation card
     */
    createProductCard(product, animalId = null) {
        const card = document.createElement('div');
        card.className = 'product-card';
        
        card.innerHTML = `
            <div class="product-info">
                <h4 class="product-name">${product.name}</h4>
                <p class="product-category">${product.category}</p>
                <span class="product-price">${product.price_range}</span>
            </div>
            <a href="${product.affiliate_url}" 
               target="_blank" 
               rel="noopener sponsored"
               class="product-link"
               onclick="app.trackProductClick('${product.product_id}', ${animalId})"
               aria-label="Buy ${product.name} on Amazon (affiliate link)">
                Shop on Amazon
            </a>
        `;
        
        return card;
    },
    
    /**
     * Create a success story card
     */
    createStoryCard(story) {
        const card = document.createElement('div');
        card.className = 'story-card';
        
        card.innerHTML = `
            <div class="story-header">
                <h4 class="story-pet-name">${story.pet_name}</h4>
                <span class="story-days">Waited ${story.days_waited} days</span>
            </div>
            <p class="story-text">${story.story_text}</p>
            ${story.adopter_name ? `<p class="story-adopter">— ${story.adopter_name}</p>` : ''}
        `;
        
        return card;
    },
    
    /**
     * Show loading spinner
     */
    showLoading(container) {
        container.innerHTML = `
            <div class="loading-spinner" role="status" aria-label="Loading...">
                <div class="spinner"></div>
                <p>Finding animals who need your help...</p>
            </div>
        `;
    },
    
    /**
     * Show error message
     */
    showError(container, message, error = null) {
        // Use user-friendly message from API error if available
        const displayMessage = (error && error.userMessage) ? error.userMessage : message;
        container.innerHTML = `
            <div class="error-message" role="alert">
                <span class="error-icon">⚠️</span>
                <h3>Connection Issue</h3>
                <p>${displayMessage}</p>
                <p class="error-hint">API: ${CONFIG.API_BASE_URL || '(not configured)'}</p>
                <button onclick="app.loadAnimals()" class="retry-button">Try Again</button>
            </div>
        `;
    },
    
    /**
     * Update stats display
     */
    updateStats(stats) {
        const statsContainer = document.getElementById('stats-container');
        if (!statsContainer) return;

        // Format data freshness timestamp if available
        let dataFreshnessHtml = '';
        if (stats.data_updated_at) {
            const dataDate = new Date(stats.data_updated_at);
            const formatted = dataDate.toLocaleString();
            dataFreshnessHtml = `<div class="data-freshness">Data last updated: ${formatted}</div>`;
        }
        
        statsContainer.innerHTML = `
            <div class="stat-item">
                <span class="stat-value">${stats.available_animals || 0}</span>
                <span class="stat-label">Animals Waiting</span>
            </div>
            <div class="stat-item">
                <span class="stat-value">${stats.longest_wait_days || 0}</span>
                <span class="stat-label">Longest Wait (Days)</span>
            </div>
            <div class="stat-item">
                <span class="stat-value">${stats.success_stories || 0}</span>
                <span class="stat-label">Happy Endings</span>
            </div>
            ${dataFreshnessHtml}
        `;
    },
    
    /**
     * Render pagination controls
     */
    renderPagination(container, currentPage, totalPages, onPageChange) {
        if (totalPages <= 1) {
            container.innerHTML = '';
            return;
        }
        
        let html = '<div class="pagination" role="navigation" aria-label="Pagination">';
        
        // Previous button
        html += `<button class="page-btn" 
                         ${currentPage <= 1 ? 'disabled' : ''} 
                         onclick="app.goToPage(${currentPage - 1})"
                         aria-label="Previous page">
                    ← Prev
                 </button>`;
        
        // Page numbers
        const startPage = Math.max(1, currentPage - 2);
        const endPage = Math.min(totalPages, currentPage + 2);
        
        if (startPage > 1) {
            html += `<button class="page-btn" onclick="app.goToPage(1)">1</button>`;
            if (startPage > 2) html += '<span class="page-ellipsis">...</span>';
        }
        
        for (let i = startPage; i <= endPage; i++) {
            html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" 
                             onclick="app.goToPage(${i})"
                             ${i === currentPage ? 'aria-current="page"' : ''}>
                        ${i}
                     </button>`;
        }
        
        if (endPage < totalPages) {
            if (endPage < totalPages - 1) html += '<span class="page-ellipsis">...</span>';
            html += `<button class="page-btn" onclick="app.goToPage(${totalPages})">${totalPages}</button>`;
        }
        
        // Next button
        html += `<button class="page-btn" 
                         ${currentPage >= totalPages ? 'disabled' : ''} 
                         onclick="app.goToPage(${currentPage + 1})"
                         aria-label="Next page">
                    Next →
                 </button>`;
        
        html += '</div>';
        container.innerHTML = html;
    },
};

// =============================================================================
// MAIN APPLICATION
// =============================================================================

const app = {
    /**
     * Initialize the application
     */
    async init() {
        console.log('🐕 Waiting The Longest - Initializing...');
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Load initial data
        await Promise.all([
            this.loadAnimals(),
            this.loadStats(),
            this.loadSuccessStories(),
        ]);
        
        console.log('✅ Application initialized');
    },
    
    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Filter form
        const filterForm = document.getElementById('filter-form');
        if (filterForm) {
            filterForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.applyFilters();
            });
            
            filterForm.addEventListener('change', () => {
                this.applyFilters();
            });
        }
        
        // Sort select
        const sortSelect = document.getElementById('sort-select');
        if (sortSelect) {
            sortSelect.addEventListener('change', (e) => {
                const [sortBy, sortOrder] = e.target.value.split('-');
                state.sortBy = sortBy;
                state.sortOrder = sortOrder;
                this.loadAnimals();
            });
        }
        
        // Search input
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            let searchTimeout;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    state.filters.breed = e.target.value;
                    state.page = 1;
                    this.loadAnimals();
                }, 300);
            });
        }
        
        // Success story form
        const storyForm = document.getElementById('success-story-form');
        if (storyForm) {
            storyForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.submitSuccessStory(new FormData(storyForm));
            });
        }
    },
    
    /**
     * Load and display animals
     */
    async loadAnimals() {
        const container = document.getElementById('animals-container');
        if (!container) return;
        
        state.isLoading = true;
        ui.showLoading(container);
        
        try {
            const response = await api.getAnimals({
                ...state.filters,
                sortBy: state.sortBy,
                sortOrder: state.sortOrder,
                page: state.page,
                pageSize: state.pageSize,
            });
            
            state.animals = response.items || [];
            state.totalPages = response.total_pages || 0;
            state.totalAnimals = response.total || 0;
            
            this.renderAnimals();
            
        } catch (error) {
            ui.showError(container, 'Failed to load animals. Please try again.', error);
            console.error('Failed to load animals:', error);
        } finally {
            state.isLoading = false;
        }
    },
    
    /**
     * Render animals to the page
     */
    renderAnimals() {
        const container = document.getElementById('animals-container');
        const paginationContainer = document.getElementById('pagination-container');
        const countDisplay = document.getElementById('animal-count');
        
        if (!container) return;
        
        // Update count
        if (countDisplay) {
            countDisplay.textContent = `${state.totalAnimals} animals waiting for a home`;
        }
        
        // Render animal cards
        if (state.animals.length === 0) {
            // Distinguish between "no filters match" vs "no data at all"
            const hasActiveFilters = Object.values(state.filters).some(v => v && v !== '');
            if (hasActiveFilters) {
                container.innerHTML = `
                    <div class="no-results">
                        <span class="no-results-icon">🔍</span>
                        <p>No animals found matching your criteria.</p>
                        <button onclick="app.clearFilters()" class="clear-filters-btn">
                            Clear Filters
                        </button>
                    </div>
                `;
            } else {
                // No data at all - empty database / new deployment
                container.innerHTML = `
                    <div class="empty-state">
                        <span class="empty-state-icon">🐾</span>
                        <h3>No Animals Yet</h3>
                        <p>We're still gathering data from shelters. Check back soon!</p>
                        <p class="empty-state-hint">If you're an admin, run the ingestion script to populate data.</p>
                    </div>
                `;
            }
        } else {
            container.innerHTML = '';
            state.animals.forEach(animal => {
                container.appendChild(ui.createAnimalCard(animal));
            });
        }
        
        // Render pagination
        if (paginationContainer) {
            ui.renderPagination(paginationContainer, state.page, state.totalPages);
        }
    },
    
    /**
     * View single animal detail
     */
    async viewAnimal(id) {
        try {
            const animal = await api.getAnimal(id);
            state.currentAnimal = animal;
            
            // Show modal or navigate to detail page
            this.showAnimalDetail(animal);
            
        } catch (error) {
            console.error('Failed to load animal:', error);
            alert('Failed to load animal details. Please try again.');
        }
    },
    
    /**
     * Show animal detail modal
     */
    showAnimalDetail(animal) {
        const modal = document.getElementById('animal-modal');
        if (!modal) {
            // Navigate to detail page instead
            window.location.href = `/animal/${animal.id}`;
            return;
        }
        
        const photoUrl = animal.photos?.[0] || animal.photo_url || '/assets/placeholder-dog.jpg';
        
        modal.innerHTML = `
            <div class="modal-overlay" onclick="app.closeModal()"></div>
            <div class="modal-content" role="dialog" aria-labelledby="modal-title">
                <button class="modal-close" onclick="app.closeModal()" aria-label="Close">&times;</button>
                
                <div class="animal-detail">
                    <div class="detail-photos">
                        <img src="${photoUrl}" alt="Photo of ${animal.canonical_name}">
                        ${animal.photos?.length > 1 ? `
                            <div class="photo-gallery">
                                ${animal.photos.map(p => `<img src="${p}" alt="">`).join('')}
                            </div>
                        ` : ''}
                    </div>
                    
                    <div class="detail-info">
                        <h2 id="modal-title">${animal.canonical_name}</h2>
                        <p class="detail-breed">${animal.breed_primary}${animal.breed_secondary ? ` / ${animal.breed_secondary}` : ''}</p>
                        
                        <div class="detail-stats">
                            <div class="stat">
                                <span class="stat-value">${animal.days_waiting}</span>
                                <span class="stat-label">Days Waiting</span>
                            </div>
                            <div class="stat">
                                <span class="stat-value">${animal.age_group}</span>
                                <span class="stat-label">Age</span>
                            </div>
                            <div class="stat">
                                <span class="stat-value">${animal.size}</span>
                                <span class="stat-label">Size</span>
                            </div>
                        </div>
                        
                        <p class="detail-description">${animal.description || 'No description available.'}</p>
                        
                        ${animal.shelter_info ? `
                            <div class="shelter-info">
                                <h3>Located at</h3>
                                <p>${animal.shelter_info.name}</p>
                                <p>${animal.shelter_info.city}, ${animal.shelter_info.state}</p>
                            </div>
                        ` : ''}
                        
                        <a href="${animal.adoption_url || '#'}" 
                           class="adopt-button-large"
                           target="_blank"
                           rel="noopener">
                            Adopt ${animal.canonical_name} Today! 🏠
                        </a>
                    </div>
                </div>
                
                <div id="product-recommendations" class="product-section">
                    <h3>Prepare for ${animal.canonical_name}'s Arrival</h3>
                    <p class="affiliate-disclosure">As an Amazon Associate, we earn from qualifying purchases.</p>
                    <div id="products-container" class="products-grid"></div>
                </div>
            </div>
        `;
        
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
        
        // Load product recommendations
        this.loadProductRecommendations(animal);
    },
    
    /**
     * Close modal
     */
    closeModal() {
        const modal = document.getElementById('animal-modal');
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }
    },
    
    /**
     * Load product recommendations for an animal
     */
    async loadProductRecommendations(animal) {
        const container = document.getElementById('products-container');
        if (!container) return;
        
        try {
            const response = await api.getProductRecommendations(
                animal.species,
                animal.age_group,
                animal.size,
                6
            );
            
            container.innerHTML = '';
            response.products.forEach(product => {
                container.appendChild(ui.createProductCard(product, animal.id));
            });
            
        } catch (error) {
            container.innerHTML = '<p>Failed to load recommendations.</p>';
            console.error('Failed to load products:', error);
        }
    },
    
    /**
     * Track product click for analytics
     */
    async trackProductClick(productId, animalId) {
        try {
            await api.trackAffiliateClick(productId, 'animal_detail', animalId);
        } catch (error) {
            console.error('Failed to track click:', error);
        }
    },
    
    /**
     * Apply filters from form
     */
    applyFilters() {
        const form = document.getElementById('filter-form');
        if (!form) return;
        
        const formData = new FormData(form);
        
        state.filters.species = formData.get('species') || '';
        state.filters.ageGroup = formData.get('age_group') || '';
        state.filters.size = formData.get('size') || '';
        state.filters.gender = formData.get('gender') || '';
        state.filters.state = formData.get('state') || '';
        state.page = 1;
        
        this.loadAnimals();
    },
    
    /**
     * Clear all filters
     */
    clearFilters() {
        const form = document.getElementById('filter-form');
        if (form) form.reset();
        
        state.filters = {
            species: '',
            breed: '',
            ageGroup: '',
            size: '',
            gender: '',
            state: '',
        };
        state.page = 1;
        
        this.loadAnimals();
    },
    
    /**
     * Go to specific page
     */
    goToPage(page) {
        if (page < 1 || page > state.totalPages) return;
        state.page = page;
        this.loadAnimals();
        
        // Scroll to top of list
        const container = document.getElementById('animals-container');
        if (container) {
            container.scrollIntoView({ behavior: 'smooth' });
        }
    },
    
    /**
     * Load platform stats
     */
    async loadStats() {
        try {
            const stats = await api.getStats();
            state.stats = stats;
            ui.updateStats(stats);
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    },
    
    /**
     * Load success stories
     */
    async loadSuccessStories() {
        const container = document.getElementById('stories-container');
        if (!container) return;
        
        try {
            const response = await api.getSuccessStories(6);
            state.successStories = response.stories || [];
            
            container.innerHTML = '';
            state.successStories.forEach(story => {
                container.appendChild(ui.createStoryCard(story));
            });
            
        } catch (error) {
            console.error('Failed to load success stories:', error);
        }
    },
    
    /**
     * Submit a success story
     */
    async submitSuccessStory(formData) {
        const story = {
            pet_name: formData.get('pet_name'),
            story_text: formData.get('story_text'),
            days_waited: parseInt(formData.get('days_waited')) || 0,
            adopter_name: formData.get('adopter_name') || null,
            contact_email: formData.get('contact_email') || null,
        };
        
        try {
            const response = await api.submitSuccessStory(story);
            
            if (response.success) {
                alert('Thank you for sharing your story! It will be reviewed and published soon.');
                document.getElementById('success-story-form').reset();
            }
        } catch (error) {
            alert('Failed to submit story. Please try again.');
            console.error('Failed to submit story:', error);
        }
    },
};

// =============================================================================
// INITIALIZATION
// =============================================================================

/**
 * Register service worker for offline support
 */
function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', async () => {
            try {
                const registration = await navigator.serviceWorker.register('/sw.js');
                console.log('[App] ServiceWorker registered:', registration.scope);
                
                // Handle updates
                registration.addEventListener('updatefound', () => {
                    const newWorker = registration.installing;
                    newWorker.addEventListener('statechange', () => {
                        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                            // New version available
                            console.log('[App] New version available');
                            // Optionally notify user about update
                        }
                    });
                });
            } catch (error) {
                console.warn('[App] ServiceWorker registration failed:', error);
            }
        });
    }
}

// Register service worker
registerServiceWorker();

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => app.init());
} else {
    app.init();
}

// Export for use in HTML
window.app = app;
window.api = api;
