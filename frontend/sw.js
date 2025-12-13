/**
 * ============================================================================
 * Waiting The Longest™ - Service Worker
 * ============================================================================
 * Purpose: Provides offline capability and caching for better performance.
 *          Implements a stale-while-revalidate strategy for API calls and
 *          cache-first for static assets.
 *
 * Features:
 *   - Offline fallback page
 *   - Static asset caching (CSS, JS, images)
 *   - API response caching with network-first strategy
 *   - Background sync for form submissions (future)
 *
 * Author: Waiting The Longest™ Development Team
 * ============================================================================
 */

const CACHE_NAME = 'wtl-cache-v1';
const STATIC_CACHE = 'wtl-static-v1';
const API_CACHE = 'wtl-api-v1';

// Static assets to cache on install
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/styles.css',
    '/app.js',
    '/manifest.json'
];

// API endpoints to cache with network-first
const API_PATTERNS = [
    '/api/animals',
    '/api/longest-waiting',
    '/api/stats',
    '/api/success-stories'
];

/**
 * Install event - cache static assets
 */
self.addEventListener('install', (event) => {
    console.log('[SW] Installing service worker...');
    
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then((cache) => {
                console.log('[SW] Caching static assets');
                return cache.addAll(STATIC_ASSETS).catch((err) => {
                    console.warn('[SW] Some static assets failed to cache:', err);
                    // Don't fail install if some assets are missing
                    return Promise.resolve();
                });
            })
            .then(() => {
                console.log('[SW] Install complete');
                return self.skipWaiting();
            })
    );
});

/**
 * Activate event - clean up old caches
 */
self.addEventListener('activate', (event) => {
    console.log('[SW] Activating service worker...');
    
    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames
                        .filter((name) => {
                            // Delete old versions of our caches
                            return name.startsWith('wtl-') && 
                                   name !== STATIC_CACHE && 
                                   name !== API_CACHE;
                        })
                        .map((name) => {
                            console.log('[SW] Deleting old cache:', name);
                            return caches.delete(name);
                        })
                );
            })
            .then(() => {
                console.log('[SW] Claiming clients');
                return self.clients.claim();
            })
    );
});

/**
 * Fetch event - handle requests with appropriate caching strategy
 */
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);
    
    // Skip non-GET requests
    if (event.request.method !== 'GET') {
        return;
    }
    
    // Skip cross-origin requests except for images
    if (url.origin !== self.location.origin && !isImageRequest(event.request)) {
        return;
    }
    
    // Check if this is an API request
    if (isApiRequest(url)) {
        event.respondWith(networkFirstWithCache(event.request, API_CACHE));
        return;
    }
    
    // Check if this is a static asset or navigation
    if (isStaticAsset(url) || event.request.mode === 'navigate') {
        event.respondWith(cacheFirstWithNetwork(event.request, STATIC_CACHE));
        return;
    }
    
    // For everything else, try network first
    event.respondWith(networkFirstWithCache(event.request, CACHE_NAME));
});

/**
 * Check if request is for an API endpoint
 */
function isApiRequest(url) {
    return url.pathname.startsWith('/api/') || 
           url.pathname === '/health';
}

/**
 * Check if request is for a static asset
 */
function isStaticAsset(url) {
    const staticExtensions = ['.html', '.css', '.js', '.json', '.ico', '.png', '.jpg', '.svg', '.woff', '.woff2'];
    return staticExtensions.some(ext => url.pathname.endsWith(ext));
}

/**
 * Check if request is for an image
 */
function isImageRequest(request) {
    return request.destination === 'image' ||
           request.url.includes('placedog.net') ||
           request.url.includes('placekitten.com');
}

/**
 * Cache-first strategy with network fallback
 * Best for static assets that don't change often
 */
async function cacheFirstWithNetwork(request, cacheName) {
    try {
        const cachedResponse = await caches.match(request);
        
        if (cachedResponse) {
            // Return cached version, but update in background
            updateCache(request, cacheName);
            return cachedResponse;
        }
        
        // Not in cache, fetch from network
        const networkResponse = await fetch(request);
        
        // Cache the response for next time
        if (networkResponse.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.warn('[SW] Cache-first fetch failed:', error);
        
        // If navigation, return offline page
        if (request.mode === 'navigate') {
            return getOfflinePage();
        }
        
        throw error;
    }
}

/**
 * Network-first strategy with cache fallback
 * Best for API data that should be fresh but available offline
 */
async function networkFirstWithCache(request, cacheName) {
    try {
        const networkResponse = await fetch(request);
        
        // Cache successful responses
        if (networkResponse.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.warn('[SW] Network fetch failed, trying cache:', error);
        
        // Network failed, try cache
        const cachedResponse = await caches.match(request);
        
        if (cachedResponse) {
            console.log('[SW] Returning cached response for:', request.url);
            return cachedResponse;
        }
        
        // Nothing in cache, return error response for API
        if (isApiRequest(new URL(request.url))) {
            return new Response(
                JSON.stringify({ 
                    error: 'Offline', 
                    message: 'Unable to connect. Please check your internet connection.' 
                }),
                {
                    status: 503,
                    statusText: 'Service Unavailable',
                    headers: { 'Content-Type': 'application/json' }
                }
            );
        }
        
        throw error;
    }
}

/**
 * Update cache in background
 */
async function updateCache(request, cacheName) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(cacheName);
            await cache.put(request, response);
        }
    } catch (error) {
        // Silent fail - cache update is best effort
        console.debug('[SW] Background cache update failed:', error);
    }
}

/**
 * Get offline fallback page
 */
async function getOfflinePage() {
    // Try to return cached index.html
    const cachedIndex = await caches.match('/index.html');
    if (cachedIndex) {
        return cachedIndex;
    }
    
    // Last resort: return a simple offline message
    return new Response(
        `<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Offline - Waiting The Longest</title>
            <style>
                body {
                    font-family: system-ui, sans-serif;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
                    text-align: center;
                    padding: 2rem;
                }
                .offline-message {
                    max-width: 400px;
                }
                h1 { color: #334155; margin-bottom: 0.5rem; }
                p { color: #64748b; }
                button {
                    background: #3b82f6;
                    color: white;
                    border: none;
                    padding: 0.75rem 1.5rem;
                    border-radius: 0.5rem;
                    cursor: pointer;
                    font-size: 1rem;
                    margin-top: 1rem;
                }
                button:hover { background: #2563eb; }
            </style>
        </head>
        <body>
            <div class="offline-message">
                <h1>🐾 You're Offline</h1>
                <p>Waiting The Longest needs an internet connection to show you animals looking for homes.</p>
                <button onclick="location.reload()">Try Again</button>
            </div>
        </body>
        </html>`,
        {
            status: 200,
            headers: { 'Content-Type': 'text/html' }
        }
    );
}

/**
 * Message handler for manual cache control
 */
self.addEventListener('message', (event) => {
    if (event.data === 'skipWaiting') {
        self.skipWaiting();
    }
    
    if (event.data === 'clearCache') {
        caches.keys().then((names) => {
            names.forEach((name) => {
                if (name.startsWith('wtl-')) {
                    caches.delete(name);
                }
            });
        });
    }
});
