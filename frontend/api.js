/**
 * Waiting The Longest™ - API Client
 * ===================================
 * JavaScript API client for frontend use
 */

const API_BASE = '/api';

/**
 * API Client configuration
 */
const config = {
  baseUrl: API_BASE,
  timeout: 30000,
  retries: 3,
  retryDelay: 1000,
};

/**
 * Custom error class for API errors
 */
class APIError extends Error {
  constructor(message, status, data = null) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.data = data;
  }
}

/**
 * Sleep utility for retry delays
 */
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * Make an API request with retry logic
 */
async function request(endpoint, options = {}) {
  const url = `${config.baseUrl}${endpoint}`;
  
  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
  };
  
  const mergedOptions = {
    ...defaultOptions,
    ...options,
    headers: {
      ...defaultOptions.headers,
      ...options.headers,
    },
  };
  
  let lastError;
  
  for (let attempt = 0; attempt <= config.retries; attempt++) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), config.timeout);
      
      const response = await fetch(url, {
        ...mergedOptions,
        signal: controller.signal,
      });
      
      clearTimeout(timeoutId);
      
      // Parse response
      const contentType = response.headers.get('content-type');
      let data;
      
      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }
      
      // Handle errors
      if (!response.ok) {
        throw new APIError(
          data.message || data.detail || 'Request failed',
          response.status,
          data
        );
      }
      
      return data;
      
    } catch (error) {
      lastError = error;
      
      // Don't retry on client errors (4xx)
      if (error instanceof APIError && error.status >= 400 && error.status < 500) {
        throw error;
      }
      
      // Don't retry on abort
      if (error.name === 'AbortError') {
        throw new APIError('Request timeout', 408);
      }
      
      // Wait before retry
      if (attempt < config.retries) {
        await sleep(config.retryDelay * (attempt + 1));
      }
    }
  }
  
  throw lastError;
}

/**
 * API methods
 */
const api = {
  /**
   * Get animals with filters and pagination
   */
  async getAnimals(params = {}) {
    const query = new URLSearchParams();
    
    if (params.species) query.set('species', params.species);
    if (params.breed) query.set('breed', params.breed);
    if (params.age) query.set('age', params.age);
    if (params.gender) query.set('gender', params.gender);
    if (params.state) query.set('state', params.state);
    if (params.page) query.set('page', params.page);
    if (params.pageSize) query.set('page_size', params.pageSize);
    if (params.sort) query.set('sort', params.sort);
    if (params.order) query.set('order', params.order);
    if (params.search) query.set('q', params.search);
    
    const queryString = query.toString();
    return request(`/animals${queryString ? `?${queryString}` : ''}`);
  },
  
  /**
   * Get single animal by ID
   */
  async getAnimal(id) {
    return request(`/animals/${id}`);
  },
  
  /**
   * Search animals
   */
  async searchAnimals(query, filters = {}) {
    const params = new URLSearchParams({ q: query, ...filters });
    return request(`/animals/search?${params}`);
  },
  
  /**
   * Get animal statistics
   */
  async getStats() {
    return request('/stats');
  },
  
  /**
   * Get list of shelters
   */
  async getShelters(params = {}) {
    const query = new URLSearchParams();
    if (params.state) query.set('state', params.state);
    if (params.page) query.set('page', params.page);
    
    const queryString = query.toString();
    return request(`/shelters${queryString ? `?${queryString}` : ''}`);
  },
  
  /**
   * Get single shelter by ID
   */
  async getShelter(id) {
    return request(`/shelters/${id}`);
  },
  
  /**
   * Get animals for a shelter
   */
  async getShelterAnimals(shelterId, params = {}) {
    const query = new URLSearchParams(params);
    return request(`/shelters/${shelterId}/animals?${query}`);
  },
  
  /**
   * Subscribe to newsletter
   */
  async subscribeNewsletter(email, preferences = {}) {
    return request('/newsletter/subscribe', {
      method: 'POST',
      body: JSON.stringify({ email, ...preferences }),
    });
  },
  
  /**
   * Share animal (track share event)
   */
  async shareAnimal(animalId, platform) {
    return request('/share', {
      method: 'POST',
      body: JSON.stringify({ animal_id: animalId, platform }),
    });
  },
  
  /**
   * Get filter options
   */
  async getFilterOptions() {
    return request('/filters');
  },
  
  /**
   * Health check
   */
  async healthCheck() {
    return request('/health');
  },
};

/**
 * Cache wrapper for API calls
 */
class CachedAPI {
  constructor(ttlMs = 60000) {
    this.cache = new Map();
    this.ttl = ttlMs;
  }
  
  async get(key, fetcher) {
    const cached = this.cache.get(key);
    
    if (cached && Date.now() - cached.timestamp < this.ttl) {
      return cached.data;
    }
    
    const data = await fetcher();
    this.cache.set(key, { data, timestamp: Date.now() });
    return data;
  }
  
  invalidate(key) {
    if (key) {
      this.cache.delete(key);
    } else {
      this.cache.clear();
    }
  }
}

const cachedApi = new CachedAPI(60000);

/**
 * Cached API methods
 */
const cached = {
  async getStats() {
    return cachedApi.get('stats', () => api.getStats());
  },
  
  async getFilterOptions() {
    return cachedApi.get('filters', () => api.getFilterOptions());
  },
  
  async getShelters() {
    return cachedApi.get('shelters', () => api.getShelters());
  },
};

/**
 * WebSocket for real-time updates
 */
class RealtimeUpdates {
  constructor() {
    this.ws = null;
    this.listeners = new Map();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }
  
  connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    try {
      this.ws = new WebSocket(wsUrl);
      
      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
      };
      
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.emit(data.type, data.payload);
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };
      
      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.reconnect();
      };
      
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    } catch (e) {
      console.error('Failed to connect WebSocket:', e);
    }
  }
  
  reconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('Max reconnect attempts reached');
      return;
    }
    
    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
    
    setTimeout(() => this.connect(), delay);
  }
  
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }
  
  off(event, callback) {
    const callbacks = this.listeners.get(event);
    if (callbacks) {
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }
  
  emit(event, data) {
    const callbacks = this.listeners.get(event);
    if (callbacks) {
      callbacks.forEach(cb => cb(data));
    }
  }
  
  disconnect() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

// Export for use
window.WTLApi = api;
window.WTLCachedApi = cached;
window.WTLRealtime = new RealtimeUpdates();
window.APIError = APIError;
