/**
 * Animal Rescue Admin Dashboard - Main Application
 *
 * Handles authentication, API calls, and UI interactions
 */

// ========================================
// State Management
// ========================================

const AppState = {
    user: null,
    accessToken: null,
    shelters: [],
    currentShelter: null,
    stats: null,
    states: [],
    pagination: {
        page: 1,
        pageSize: CONFIG.APP.PAGE_SIZE,
        total: 0
    },
    filters: {
        query: '',
        state: '',
        type: '',
        verifiedOnly: false
    }
};

// ========================================
// Utility Functions
// ========================================

function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, CONFIG.APP.TOAST_DURATION);
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatOrgType(type) {
    if (!type) return 'Unknown';
    return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

// ========================================
// Authentication
// ========================================

function parseHashParams() {
    const hash = window.location.hash.substring(1);
    const params = {};
    hash.split('&').forEach(pair => {
        const [key, value] = pair.split('=');
        if (key) params[key] = decodeURIComponent(value || '');
    });
    return params;
}

function checkAuthOnLoad() {
    // Check for token in URL hash (OAuth redirect)
    const hashParams = parseHashParams();
    if (hashParams.access_token) {
        AppState.accessToken = hashParams.access_token;
        localStorage.setItem('access_token', hashParams.access_token);
        // Clear hash from URL
        history.replaceState(null, '', window.location.pathname);
    }

    // Check for stored token
    const storedToken = localStorage.getItem('access_token');
    if (storedToken) {
        AppState.accessToken = storedToken;
        validateToken();
    } else {
        showLoginScreen();
    }
}

async function validateToken() {
    try {
        const response = await fetch(`${CONFIG.API.BASE_URL}${CONFIG.API.ENDPOINTS.STATS}`, {
            headers: {
                'Authorization': `Bearer ${AppState.accessToken}`
            }
        });

        if (response.ok) {
            // Token is valid, get user info
            const email = parseTokenForEmail(AppState.accessToken);
            AppState.user = { email };
            showDashboard();
        } else {
            // Token invalid or expired
            logout();
        }
    } catch (error) {
        console.error('Token validation error:', error);
        logout();
    }
}

function parseTokenForEmail(token) {
    try {
        const payload = token.split('.')[1];
        const decoded = JSON.parse(atob(payload));
        return decoded.email || decoded['cognito:username'] || 'Admin User';
    } catch {
        return 'Admin User';
    }
}

function login() {
    window.location.href = CONFIG.AUTH.LOGIN_URL;
}

function logout() {
    AppState.user = null;
    AppState.accessToken = null;
    localStorage.removeItem('access_token');
    showLoginScreen();
}

function showLoginScreen() {
    document.getElementById('login-screen').classList.remove('hidden');
    document.getElementById('dashboard-screen').classList.add('hidden');
}

function showDashboard() {
    document.getElementById('login-screen').classList.add('hidden');
    document.getElementById('dashboard-screen').classList.remove('hidden');

    document.getElementById('user-email').textContent = AppState.user?.email || '';

    // Load initial data
    loadStats();
    loadStates();
    searchShelters();
}

// ========================================
// API Functions
// ========================================

async function apiCall(endpoint, options = {}) {
    const url = `${CONFIG.API.BASE_URL}${endpoint}`;
    const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${AppState.accessToken}`,
        ...options.headers
    };

    try {
        const response = await fetch(url, {
            ...options,
            headers
        });

        if (response.status === 401) {
            logout();
            throw new Error('Session expired');
        }

        return await response.json();
    } catch (error) {
        console.error('API error:', error);
        throw error;
    }
}

async function loadStats() {
    try {
        const stats = await apiCall(CONFIG.API.ENDPOINTS.STATS);
        AppState.stats = stats;
        updateStatsDisplay();
    } catch (error) {
        showToast('Failed to load statistics', 'error');
    }
}

async function loadStates() {
    try {
        const data = await apiCall(CONFIG.API.ENDPOINTS.STATES);
        AppState.states = data.states || [];
        populateStateFilter();
    } catch (error) {
        console.error('Failed to load states:', error);
    }
}

async function searchShelters() {
    const { query, state, type, verifiedOnly } = AppState.filters;
    const { page, pageSize } = AppState.pagination;
    const offset = (page - 1) * pageSize;

    let url = `${CONFIG.API.ENDPOINTS.SHELTERS}?limit=${pageSize}&offset=${offset}`;
    if (query) url += `&q=${encodeURIComponent(query)}`;
    if (state) url += `&state=${encodeURIComponent(state)}`;
    if (type) url += `&type=${encodeURIComponent(type)}`;
    if (verifiedOnly) url += `&verified=true`;

    try {
        showLoading();
        const data = await apiCall(url);
        AppState.shelters = data.shelters || [];
        AppState.pagination.total = data.total || 0;
        renderResults();
    } catch (error) {
        showToast('Failed to search shelters', 'error');
        renderResults();
    }
}

async function loadShelter(shelterId) {
    try {
        const shelter = await apiCall(`${CONFIG.API.ENDPOINTS.SHELTERS}/${shelterId}`);
        AppState.currentShelter = shelter;
        openModal(shelter);
    } catch (error) {
        showToast('Failed to load shelter details', 'error');
    }
}

async function saveShelter() {
    if (!AppState.currentShelter) return;

    const updates = {
        name: document.getElementById('detail-name').value,
        org_type: document.getElementById('detail-type').value,
        phone: document.getElementById('detail-phone').value,
        email: document.getElementById('detail-email').value,
        website: document.getElementById('detail-website').value,
        address: document.getElementById('detail-address').value,
        city: document.getElementById('detail-city').value,
        state: document.getElementById('detail-state').value.toUpperCase(),
        zip_code: document.getElementById('detail-zip').value,
        description: document.getElementById('detail-description').value,
        notes: document.getElementById('detail-notes').value,
        verified: document.getElementById('detail-verified').checked
    };

    try {
        await apiCall(`${CONFIG.API.ENDPOINTS.SHELTERS}/${AppState.currentShelter.shelter_id}`, {
            method: 'PUT',
            body: JSON.stringify(updates)
        });

        showToast('Changes saved successfully');
        closeModal();
        searchShelters(); // Refresh results
    } catch (error) {
        showToast('Failed to save changes', 'error');
    }
}

// ========================================
// UI Functions
// ========================================

function updateStatsDisplay() {
    if (!AppState.stats) return;

    document.getElementById('stat-total').textContent =
        AppState.stats.total_shelters?.toLocaleString() || '--';
    document.getElementById('stat-states').textContent =
        `${AppState.stats.states_completed || 0}/50`;
    document.getElementById('stat-verified').textContent =
        AppState.stats.verified_count?.toLocaleString() || '--';
    document.getElementById('stat-pending').textContent =
        AppState.stats.states_pending || '--';
}

function populateStateFilter() {
    const select = document.getElementById('filter-state');
    // Clear existing options except "All States"
    select.innerHTML = '<option value="">All States</option>';

    // Sort states alphabetically by full name
    const sortedStates = [...AppState.states].sort((a, b) =>
        (a.state_full || a.state).localeCompare(b.state_full || b.state)
    );

    sortedStates.forEach(state => {
        const option = document.createElement('option');
        option.value = state.state;
        option.textContent = `${state.state_full || state.state} (${state.shelter_count || 0})`;
        select.appendChild(option);
    });
}

function showLoading() {
    document.getElementById('results-list').innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
        </div>
    `;
}

function renderResults() {
    const container = document.getElementById('results-list');
    const { shelters } = AppState;
    const { total, page, pageSize } = AppState.pagination;

    // Update count
    document.getElementById('results-count').textContent =
        `${total.toLocaleString()} organizations found`;

    // Update pagination
    const totalPages = Math.ceil(total / pageSize);
    document.getElementById('page-info').textContent = `Page ${page} of ${totalPages || 1}`;
    document.getElementById('prev-page').disabled = page <= 1;
    document.getElementById('next-page').disabled = page >= totalPages;

    if (shelters.length === 0) {
        container.innerHTML = `
            <div class="loading">
                No organizations found. Try adjusting your search.
            </div>
        `;
        return;
    }

    container.innerHTML = shelters.map(shelter => `
        <div class="result-card" onclick="loadShelter('${shelter.shelter_id}')">
            <div class="result-info">
                <div class="result-name">${escapeHtml(shelter.name)}</div>
                <div class="result-location">
                    ${escapeHtml(shelter.city || '')}${shelter.city && shelter.state ? ', ' : ''}${shelter.state || ''}
                </div>
                <div class="result-contact">
                    ${shelter.phone ? `<span>Phone: ${escapeHtml(shelter.phone)}</span>` : ''}
                    ${shelter.email ? `<span>Email: ${escapeHtml(shelter.email)}</span>` : ''}
                </div>
            </div>
            <div class="result-badges">
                <span class="type-badge">${formatOrgType(shelter.org_type)}</span>
                ${shelter.verified ? '<span class="verified-badge">Verified</span>' : ''}
                ${shelter.notes ? '<span class="has-notes-badge">Has Notes</span>' : ''}
            </div>
        </div>
    `).join('');
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function openModal(shelter) {
    document.getElementById('modal-title').textContent = shelter.name || 'Organization Details';

    // Populate fields
    document.getElementById('detail-name').value = shelter.name || '';
    document.getElementById('detail-type').value = shelter.org_type || 'nonprofit';
    document.getElementById('detail-phone').value = shelter.phone || '';
    document.getElementById('detail-email').value = shelter.email || '';
    document.getElementById('detail-website').value = shelter.website || '';
    document.getElementById('detail-address').value = shelter.address || '';
    document.getElementById('detail-city').value = shelter.city || '';
    document.getElementById('detail-state').value = shelter.state || '';
    document.getElementById('detail-zip').value = shelter.zip_code || '';
    document.getElementById('detail-description').value = shelter.description || '';
    document.getElementById('detail-notes').value = shelter.notes || '';
    document.getElementById('detail-verified').checked = shelter.verified || false;

    // Meta information
    document.getElementById('detail-id').textContent = shelter.shelter_id || 'N/A';
    document.getElementById('detail-source').textContent = shelter.source || 'N/A';
    document.getElementById('detail-collected').textContent = formatDate(shelter.collected_at);
    document.getElementById('detail-updated').textContent = formatDate(shelter.last_updated);

    // Notes meta
    if (shelter.notes_updated_at) {
        document.getElementById('notes-meta').textContent =
            `Last updated by ${shelter.notes_updated_by || 'Unknown'} on ${formatDate(shelter.notes_updated_at)}`;
    } else {
        document.getElementById('notes-meta').textContent = '';
    }

    // Verified meta
    if (shelter.verified && shelter.verified_at) {
        document.getElementById('verified-meta').textContent =
            `Verified by ${shelter.verified_by || 'Unknown'} on ${formatDate(shelter.verified_at)}`;
    } else {
        document.getElementById('verified-meta').textContent = '';
    }

    document.getElementById('detail-modal').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('detail-modal').classList.add('hidden');
    AppState.currentShelter = null;
}

// ========================================
// Event Handlers
// ========================================

function setupEventListeners() {
    // Login button
    document.getElementById('google-login-btn').addEventListener('click', login);

    // Logout button
    document.getElementById('logout-btn').addEventListener('click', logout);

    // Search
    document.getElementById('search-btn').addEventListener('click', () => {
        AppState.filters.query = document.getElementById('search-input').value;
        AppState.pagination.page = 1;
        searchShelters();
    });

    document.getElementById('search-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            AppState.filters.query = e.target.value;
            AppState.pagination.page = 1;
            searchShelters();
        }
    });

    // Filters
    document.getElementById('filter-state').addEventListener('change', (e) => {
        AppState.filters.state = e.target.value;
        AppState.pagination.page = 1;
        searchShelters();
    });

    document.getElementById('filter-type').addEventListener('change', (e) => {
        AppState.filters.type = e.target.value;
        AppState.pagination.page = 1;
        searchShelters();
    });

    document.getElementById('filter-verified').addEventListener('change', (e) => {
        AppState.filters.verifiedOnly = e.target.checked;
        AppState.pagination.page = 1;
        searchShelters();
    });

    // Pagination
    document.getElementById('prev-page').addEventListener('click', () => {
        if (AppState.pagination.page > 1) {
            AppState.pagination.page--;
            searchShelters();
        }
    });

    document.getElementById('next-page').addEventListener('click', () => {
        const totalPages = Math.ceil(AppState.pagination.total / AppState.pagination.pageSize);
        if (AppState.pagination.page < totalPages) {
            AppState.pagination.page++;
            searchShelters();
        }
    });

    // Save button in modal
    document.getElementById('save-btn').addEventListener('click', saveShelter);

    // Close modal on backdrop click
    document.getElementById('detail-modal').addEventListener('click', (e) => {
        if (e.target.id === 'detail-modal') {
            closeModal();
        }
    });

    // Close modal on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeModal();
        }
    });
}

// ========================================
// Initialization
// ========================================

document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    checkAuthOnLoad();
});
