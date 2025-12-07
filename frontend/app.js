/**
 * ============================================================================
 * Waiting The Longest™ - Frontend Application
 * ============================================================================
 * "Help shorten the road home"
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

const resolveApiBaseUrl = () => {
    const override = document.documentElement?.getAttribute('data-api-base');
    if (override) {
        return override;
    }

    const origin = window.location.origin;
    const isLocal = origin.includes('localhost') || origin.includes('127.0.0.1');
    if (isLocal) {
        return 'http://127.0.0.1:8000';
    }

    return origin;
};

const CONFIG = {
    API_BASE_URL: resolveApiBaseUrl(),
    DEFAULT_PAGE_SIZE: 20,
    AFFILIATE_TAG: 'waitingthelon-20',
    CACHE_TTL: 5 * 60 * 1000, // 5 minutes
};

window.__WTL_API_BASE__ = CONFIG.API_BASE_URL;

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
            console.error('API request failed:', error);
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
     * Get paginated list of shelters
     */
    async getShelters(params = {}) {
        const queryParams = new URLSearchParams();
        
        if (params.search) queryParams.set('search', params.search);
        if (params.state) queryParams.set('state', params.state);
        if (params.page) queryParams.set('page', params.page);
        if (params.pageSize) queryParams.set('page_size', params.pageSize);
        
        return this.request(`/api/shelters?${queryParams.toString()}`);
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
        
        const photoUrl = animal.photo_url || 'https://placedog.net/400/300';
        const daysWaiting = animal.days_waiting || 0;
        const urgencyClass = daysWaiting > 365 ? 'urgent' : daysWaiting > 180 ? 'warning' : '';
        
        card.innerHTML = `
            <div class="animal-photo">
                <img src="${photoUrl}" 
                     alt="Photo of ${animal.canonical_name}, a ${animal.breed_primary}" 
                     loading="lazy"
                     onerror="this.src='https://placedog.net/400/300'">
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
            <div class="animal-actions" style="display: flex; gap: 0.5rem; margin-top: 1rem;">
                <button class="adopt-button" 
                        style="flex: 1;"
                        onclick="app.viewAnimal(${animal.id})"
                        aria-label="Learn more about ${animal.canonical_name}">
                    Meet ${animal.canonical_name || 'Me'} 💕
                </button>
                <button class="btn btn-outline" 
                        style="padding: 0.5rem;"
                        onclick="app.openDonationModal('${animal.canonical_name}', '${animal.shelter_id}')"
                        aria-label="Donate to help ${animal.canonical_name}">
                    🎁 Donate
                </button>
            </div>
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
    showError(container, message) {
        container.innerHTML = `
            <div class="error-message" role="alert">
                <span class="error-icon">⚠️</span>
                <p>${message}</p>
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
            this.loadFeaturedAnimal(),
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
     * Load and display featured animal (longest waiting)
     */
    async loadFeaturedAnimal() {
        const container = document.getElementById('featured-animal');
        if (!container) return;

        try {
            // Get the single longest waiting animal
            const response = await api.getLongestWaiting(null, 1);
            const animals = response.animals || response.items || [];
            
            if (animals.length > 0) {
                const animal = animals[0];
                this.renderFeaturedAnimal(container, animal);
                container.style.display = 'block';
            }
        } catch (error) {
            console.error('Failed to load featured animal:', error);
            container.style.display = 'none';
        }
    },

    /**
     * Render featured animal
     */
    renderFeaturedAnimal(container, animal) {
        const photoUrl = animal.photos?.[0] || animal.photo_url || 'https://placedog.net/800/600';
        const daysWaiting = animal.days_waiting || 0;
        
        container.innerHTML = `
            <div class="featured-card">
                <div class="featured-header">
                    <h2>
                        <span class="highlight-name">${animal.canonical_name}</span> has been waiting the longest of any pet we know of to find a home.
                    </h2>
                    <p class="featured-cta">
                        If you'd like to bring <span class="highlight-name">${animal.canonical_name}</span> home today, 
                        <a href="/animal.html?id=${animal.id}" class="featured-link">click here</a>
                    </p>
                </div>
                <div class="featured-image-container">
                    <img src="${photoUrl}" 
                         alt="${animal.canonical_name} - Waiting ${daysWaiting} days" 
                         class="featured-image">
                    <div class="featured-badge">${daysWaiting} Days Waiting</div>
                </div>
            </div>
        `;
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
            ui.showError(container, 'Failed to load animals. Please try again.');
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
        
        if (window.location.pathname.includes('shelters.html')) {
            loadShelters();
            const container = document.getElementById('shelters-grid');
            if (container) {
                container.scrollIntoView({ behavior: 'smooth' });
            }
        } else {
            this.loadAnimals();
            // Scroll to top of list
            const container = document.getElementById('animals-container');
            if (container) {
                container.scrollIntoView({ behavior: 'smooth' });
            }
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

    /**
     * Open Donation Modal
     */
    openDonationModal(animalName, shelterId) {
        // Create modal if it doesn't exist
        let modal = document.getElementById('donation-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'donation-modal';
            modal.className = 'modal';
            document.body.appendChild(modal);
        }

        modal.innerHTML = `
            <div class="modal-overlay" onclick="document.getElementById('donation-modal').classList.remove('active')"></div>
            <div class="modal-content" style="max-width: 500px;">
                <button class="modal-close" onclick="document.getElementById('donation-modal').classList.remove('active')">&times;</button>
                
                <div style="text-align: center; padding: 1rem;">
                    <h2 style="margin-bottom: 1rem;">Donate to Help ${animalName}</h2>
                    <p style="color: #666; margin-bottom: 2rem;">Your donation goes directly to the shelter caring for ${animalName}.</p>
                    
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 2rem;">
                        <button class="btn btn-outline" onclick="selectAmount(10)">$10</button>
                        <button class="btn btn-outline" onclick="selectAmount(25)">$25</button>
                        <button class="btn btn-outline" onclick="selectAmount(50)">$50</button>
                    </div>
                    
                    <div style="margin-bottom: 2rem;">
                        <label style="display: block; text-align: left; margin-bottom: 0.5rem; font-weight: 500;">Custom Amount</label>
                        <div style="display: flex; align-items: center;">
                            <span style="font-size: 1.2rem; margin-right: 0.5rem;">$</span>
                            <input type="number" id="custom-amount" class="form-input" placeholder="0.00" style="flex: 1;">
                        </div>
                    </div>
                    
                    <button class="btn btn-primary btn-large" style="width: 100%;" onclick="processDonation('${animalName}')">
                        Donate Now 💳
                    </button>
                    
                    <p style="font-size: 0.8rem; color: #999; margin-top: 1rem;">
                        Secure payment processing via Stripe. 100% of your donation (minus processing fees) goes to the shelter.
                    </p>
                </div>
            </div>
        `;
        
        // Add helper functions to window scope for the modal
        window.selectAmount = (amount) => {
            document.getElementById('custom-amount').value = amount;
        };
        
        window.processDonation = (name) => {
            const amount = document.getElementById('custom-amount').value;
            if (!amount || amount <= 0) {
                alert('Please enter a valid donation amount.');
                return;
            }
            alert(`Thank you for your generous donation of $${amount} to help ${name}! (This is a demo)`);
            document.getElementById('donation-modal').classList.remove('active');
        };

        // Show modal
        setTimeout(() => modal.classList.add('active'), 10);
    },
};

// =============================================================================
// INITIALIZATION
// =============================================================================

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => app.init());
} else {
    app.init();
}

// Export for use in HTML
window.app = app;
window.api = api;
window.state = state;
window.loadShelters = loadShelters;

/**
 * Load and display shelters
 */
async function loadShelters() {
    const container = document.getElementById('shelters-grid');
    if (!container) return;
    
    const searchInput = document.getElementById('shelter-search');
    const searchTerm = searchInput ? searchInput.value : '';

    const stateInput = document.getElementById('shelter-state');
    const stateFilter = stateInput ? stateInput.value : '';
    
    container.innerHTML = '<div class="loading-spinner"></div>';
    
    try {
        const response = await api.getShelters({
            search: searchTerm,
            state: stateFilter,
            page: state.page,
            pageSize: state.pageSize
        });
        
        state.totalPages = response.total_pages || 0;
        
        renderShelters(response.items || []);
        
        const paginationContainer = document.getElementById('pagination');
        if (paginationContainer) {
            ui.renderPagination(paginationContainer, state.page, state.totalPages);
        }
        
    } catch (error) {
        console.error('Failed to load shelters:', error);
        container.innerHTML = '<p>Failed to load shelters. Please try again later.</p>';
    }
}

/**
 * Check if user is logged in
 */
function isLoggedIn() {
    return !!localStorage.getItem('user_token');
}

/**
 * Render shelters grid
 */
function renderShelters(shelters) {
    const container = document.getElementById('shelters-grid');
    if (!container) return;
    
    if (shelters.length === 0) {
        container.innerHTML = '<p>No shelters found matching your criteria.</p>';
        return;
    }
    
    const userLoggedIn = isLoggedIn();
    
    container.innerHTML = shelters.map(shelter => `
        <div class="shelter-card">
            <div class="shelter-name">${shelter.name}</div>
            <div class="shelter-location">
                <span>📍</span>
                ${shelter.city || 'Unknown City'}, ${shelter.state || 'Unknown State'}
            </div>
            
            <div class="shelter-stats">
                <span class="stat-badge">${shelter.total_animals || 0} Animals</span>
            </div>
            
            <div class="shelter-contact">
                ${userLoggedIn ? `
                    ${shelter.phone ? `
                        <div class="contact-item">
                            <span>📞</span>
                            <a href="tel:${shelter.phone}">${shelter.phone}</a>
                        </div>
                    ` : ''}
                    
                    ${shelter.email ? `
                        <div class="contact-item">
                            <span>✉️</span>
                            <a href="mailto:${shelter.email}">${shelter.email}</a>
                        </div>
                    ` : ''}
                    
                    ${shelter.website ? `
                        <div class="contact-item">
                            <span>🌐</span>
                            <a href="${shelter.website}" target="_blank" rel="noopener">Visit Website</a>
                        </div>
                    ` : ''}
                ` : `
                    <div class="contact-lock" style="text-align: center; padding: 1rem; background: #f8f9fa; border-radius: 8px; margin-top: 0.5rem;">
                        <span style="font-size: 1.5rem; display: block; margin-bottom: 0.5rem;">🔒</span>
                        <p style="font-size: 0.9rem; color: #666; margin-bottom: 0.5rem;">Contact info is locked</p>
                        <a href="login.html" class="btn btn-primary btn-small" style="font-size: 0.8rem; padding: 0.25rem 0.75rem;">Log in to view</a>
                    </div>
                `}
            </div>
        </div>
    `).join('');
}

function setRescueSummaryState(message) {
    const summaryContainer = document.getElementById('rescue-directory-summary');
    if (summaryContainer) {
        summaryContainer.innerHTML = `<p class="rescue-summary-message">${message}</p>`;
    }
}

function renderRescueSummary(directory) {
    const summaryContainer = document.getElementById('rescue-directory-summary');
    if (!summaryContainer) return;

    const counts = directory.counts || {};
    const metadata = directory.metadata || {};

    const formatNumber = (value) => typeof value === 'number'
        ? value.toLocaleString()
        : '—';

    const formattedDate = metadata.generated_at
        ? new Date(metadata.generated_at).toLocaleDateString(undefined, {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        })
        : 'Recently synced';

    const sources = Array.isArray(metadata.sources)
        ? metadata.sources.slice(0, 2).join(' • ')
        : 'Multiple partner briefings';

    summaryContainer.innerHTML = `
        <div class="rescue-summary-grid">
            <article class="rescue-metric">
                <span class="metric-label">MA Partners</span>
                <span class="metric-value">${formatNumber(counts.state_entries)}</span>
                <p>Licensed Commonwealth rescues we verify monthly.</p>
            </article>
            <article class="rescue-metric">
                <span class="metric-label">Transport Hubs</span>
                <span class="metric-value">${formatNumber(counts.network_entries)}</span>
                <p>High-volume partners across ${formatNumber(counts.network_regions)} corridors.</p>
            </article>
            <article class="rescue-metric">
                <span class="metric-label">AKC Breeds</span>
                <span class="metric-value">${formatNumber(counts.akc_entries)}</span>
                <p>Safety-net coordinators for complex breed needs.</p>
            </article>
        </div>
        <div class="rescue-summary-meta">
            <span>Dataset v${metadata.version || 'n/a'}</span>
            <span>Updated ${formattedDate}</span>
            <span>${sources}</span>
        </div>
    `;
}

async function loadRescueDirectoryHighlights() {
    const curatedContainer = document.getElementById('curated-rescue-grid');
    const nationalContainer = document.getElementById('national-transport-sections');
    const akcContainer = document.getElementById('akc-network-grid');

    if (!curatedContainer && !nationalContainer && !akcContainer) {
        return;
    }

    const setLoading = (el) => {
        if (el) {
            el.innerHTML = '<div class="loading-spinner"></div>';
        }
    };

    setLoading(curatedContainer);
    setLoading(nationalContainer);
    setLoading(akcContainer);
    setRescueSummaryState('Loading directory insights...');

    try {
        const directory = await api.request('/api/resources/rescues');

        renderRescueSummary(directory);

        if (curatedContainer) {
            const entries = (directory.states?.massachusetts || []).slice(0, 9);
            curatedContainer.innerHTML = entries.map(renderRescueCard).join('') || '<p>No curated rescues available.</p>';
        }

        if (nationalContainer) {
            nationalContainer.innerHTML = renderNetworkSections(directory.national || {});
        }

        if (akcContainer) {
            const breedEntries = directory.akc_network || [];
            akcContainer.innerHTML = breedEntries.map(renderAkcCard).join('') || '<p>No AKC breed data available.</p>';
        }
    } catch (error) {
        console.error('Failed to load rescue directory:', error);
        const errorHtml = `<p style="color: #c53030;">Unable to load rescue directory: ${error.message}</p>`;
        if (curatedContainer) curatedContainer.innerHTML = errorHtml;
        if (nationalContainer) nationalContainer.innerHTML = errorHtml;
        if (akcContainer) akcContainer.innerHTML = errorHtml;
        setRescueSummaryState(`Unable to load directory insights: ${error.message}`);
    }
}

function renderRescueCard(entry) {
    const contactBlocks = [
        entry.phone ? `<div class="contact-item"><span>📞</span><a href="tel:${entry.phone}">${entry.phone}</a></div>` : '',
        entry.email ? `<div class="contact-item"><span>✉️</span><a href="mailto:${entry.email}">${entry.email}</a></div>` : '',
        entry.website ? `<div class="contact-item"><span>🌐</span><a href="${entry.website}" target="_blank" rel="noopener">Website</a></div>` : ''
    ].join('');

    const tags = (entry.focus || []).map(tag => `<span class="stat-badge">${tag}</span>`).join('');

    return `
        <article class="shelter-card">
            <div class="shelter-name">${entry.name}</div>
            <div class="shelter-location"><span>📍</span>${entry.location || ''}</div>
            <p style="color:#4a5568; font-size:0.9rem;">${entry.description || ''}</p>
            <div class="shelter-stats">${tags}</div>
            <div class="shelter-contact">${contactBlocks}</div>
        </article>
    `;
}

function renderNetworkSections(national = {}) {
    const sections = Object.entries(national);
    if (!sections.length) {
        return '<p>No national transport data available.</p>';
    }

    return sections.map(([region, entries]) => {
        const cards = (entries || []).map(item => `
            <div class="network-card">
                <div class="network-card-header">
                    <div>
                        <h4>${item.name}</h4>
                        <p>${item.description || ''}</p>
                    </div>
                    <span class="network-region">${item.region || region}</span>
                </div>
                <div class="network-meta">
                    ${item.contact ? `<span>📞 ${item.contact}</span>` : ''}
                    ${item.website ? `<a href="${item.website}" target="_blank" rel="noopener">Visit site →</a>` : ''}
                </div>
            </div>
        `).join('');

        return `
            <section class="network-section">
                <h3>${region.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</h3>
                ${cards || '<p>No partners listed.</p>'}
            </section>
        `;
    }).join('');
}

function renderAkcCard(entry) {
    const contactRows = (entry.contacts || []).map(contact => `
        <div class="contact-item">
            <strong>${contact.name || contact.organization}</strong>
            ${contact.phone ? `<span>• ${contact.phone}</span>` : ''}
            ${contact.email ? `<a href="mailto:${contact.email}">${contact.email}</a>` : ''}
        </div>
    `).join('');

    return `
        <article class="akc-card">
            <h4>${entry.breed}</h4>
            <p>${entry.context || ''}</p>
            <div class="akc-contact-list">${contactRows}</div>
        </article>
    `;
}

window.loadRescueDirectoryHighlights = loadRescueDirectoryHighlights;

