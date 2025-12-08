/**
 * ============================================================================
 * Waiting The Longest™ - Service Worker
 * ============================================================================
 * Provides offline caching and performance optimization
 *
 * Cache Strategy:
 * - Static assets: Cache first, network fallback
 * - API calls: Network first, cache fallback
 * - Images: Cache first with network update
 * ============================================================================
 */

const CACHE_VERSION = 'wtl-v1.0.0';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const DYNAMIC_CACHE = `${CACHE_VERSION}-dynamic`;
const IMAGE_CACHE = `${CACHE_VERSION}-images`;

// Static assets to cache immediately
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/about.html',
    '/contact.html',
    '/stories.html',
    '/shelters.html',
    '/404.html',
    '/styles.css',
    '/app.js',
    '/manifest.json',
    '/images/logo.png'
];

// Maximum cache sizes
const MAX_DYNAMIC_CACHE_SIZE = 50;
const MAX_IMAGE_CACHE_SIZE = 100;

/**
 * Install event - cache static assets
 */
self.addEventListener('install', (event) => {
    console.log('[Service Worker] Installing...', CACHE_VERSION);

    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then((cache) => {
                console.log('[Service Worker] Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => {
                console.log('[Service Worker] Skip waiting');
                return self.skipWaiting();
            })
            .catch((error) => {
                console.error('[Service Worker] Installation failed:', error);
            })
    );
});

/**
 * Activate event - clean up old caches
 */
self.addEventListener('activate', (event) => {
    console.log('[Service Worker] Activating...', CACHE_VERSION);

    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames
                        .filter((name) => {
                            return name.startsWith('wtl-') && name !== STATIC_CACHE &&
                                   name !== DYNAMIC_CACHE && name !== IMAGE_CACHE;
                        })
                        .map((name) => {
                            console.log('[Service Worker] Deleting old cache:', name);
                            return caches.delete(name);
                        })
                );
            })
            .then(() => {
                console.log('[Service Worker] Claiming clients');
                return self.clients.claim();
            })
    );
});

/**
 * Fetch event - serve from cache or network
 */
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }

    // Skip chrome extensions and other protocols
    if (!url.protocol.startsWith('http')) {
        return;
    }

    // API requests - Network first, cache fallback
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(networkFirstStrategy(request, DYNAMIC_CACHE));
        return;
    }

    // Images - Cache first, network update
    if (request.destination === 'image' || url.pathname.match(/\.(jpg|jpeg|png|gif|webp|svg)$/i)) {
        event.respondWith(cacheFirstStrategy(request, IMAGE_CACHE, MAX_IMAGE_CACHE_SIZE));
        return;
    }

    // Static assets - Cache first, network fallback
    if (STATIC_ASSETS.includes(url.pathname) || url.pathname.match(/\.(css|js|woff2|woff|ttf)$/i)) {
        event.respondWith(cacheFirstStrategy(request, STATIC_CACHE));
        return;
    }

    // HTML pages - Network first, cache fallback
    if (request.headers.get('Accept')?.includes('text/html')) {
        event.respondWith(networkFirstStrategy(request, DYNAMIC_CACHE));
        return;
    }

    // Default: Network with cache fallback
    event.respondWith(networkFirstStrategy(request, DYNAMIC_CACHE));
});

/**
 * Cache first strategy - serve from cache, update from network
 */
async function cacheFirstStrategy(request, cacheName, maxSize = null) {
    try {
        const cache = await caches.open(cacheName);
        const cachedResponse = await cache.match(request);

        if (cachedResponse) {
            // Return cached response and update in background
            updateCache(request, cache, maxSize);
            return cachedResponse;
        }

        // Not in cache, fetch from network
        const networkResponse = await fetch(request);

        if (networkResponse && networkResponse.status === 200) {
            await addToCache(cache, request, networkResponse.clone(), maxSize);
        }

        return networkResponse;

    } catch (error) {
        console.error('[Service Worker] Cache first strategy failed:', error);

        // Return offline fallback for images
        if (request.destination === 'image') {
            return createOfflineImageResponse();
        }

        throw error;
    }
}

/**
 * Network first strategy - fetch from network, fallback to cache
 */
async function networkFirstStrategy(request, cacheName) {
    try {
        const networkResponse = await fetch(request);

        // Cache successful responses
        if (networkResponse && networkResponse.status === 200) {
            const cache = await caches.open(cacheName);
            await addToCache(cache, request, networkResponse.clone(), MAX_DYNAMIC_CACHE_SIZE);
        }

        return networkResponse;

    } catch (error) {
        console.log('[Service Worker] Network failed, checking cache:', request.url);

        const cache = await caches.open(cacheName);
        const cachedResponse = await cache.match(request);

        if (cachedResponse) {
            console.log('[Service Worker] Serving from cache:', request.url);
            return cachedResponse;
        }

        // Return offline page for HTML requests
        if (request.headers.get('Accept')?.includes('text/html')) {
            const offlineResponse = await cache.match('/404.html');
            if (offlineResponse) {
                return offlineResponse;
            }
        }

        throw error;
    }
}

/**
 * Update cache in background
 */
async function updateCache(request, cache, maxSize) {
    try {
        const networkResponse = await fetch(request);
        if (networkResponse && networkResponse.status === 200) {
            await addToCache(cache, request, networkResponse, maxSize);
        }
    } catch (error) {
        // Silent fail - we already have cached version
    }
}

/**
 * Add to cache with size limit
 */
async function addToCache(cache, request, response, maxSize) {
    await cache.put(request, response);

    if (maxSize) {
        await limitCacheSize(cache, maxSize);
    }
}

/**
 * Limit cache size by removing oldest entries
 */
async function limitCacheSize(cache, maxSize) {
    const keys = await cache.keys();

    if (keys.length > maxSize) {
        const deleteCount = keys.length - maxSize;
        for (let i = 0; i < deleteCount; i++) {
            await cache.delete(keys[i]);
        }
    }
}

/**
 * Create offline image placeholder
 */
function createOfflineImageResponse() {
    // Return a simple SVG placeholder
    const svg = `
        <svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
            <rect width="400" height="300" fill="#F1F5F9"/>
            <text x="50%" y="50%" text-anchor="middle" dy=".3em"
                  font-family="Arial, sans-serif" font-size="16" fill="#64748B">
                Offline - Image not cached
            </text>
        </svg>
    `;

    return new Response(svg, {
        headers: {
            'Content-Type': 'image/svg+xml',
            'Cache-Control': 'no-store'
        }
    });
}

/**
 * Background sync for form submissions
 */
self.addEventListener('sync', (event) => {
    console.log('[Service Worker] Background sync:', event.tag);

    if (event.tag === 'sync-success-stories') {
        event.waitUntil(syncSuccessStories());
    }
});

/**
 * Sync pending success stories
 */
async function syncSuccessStories() {
    // This would sync any queued form submissions
    // Implementation depends on your data storage strategy
    console.log('[Service Worker] Syncing success stories...');
}

/**
 * Push notification handler
 */
self.addEventListener('push', (event) => {
    console.log('[Service Worker] Push notification received');

    const data = event.data ? event.data.json() : {};
    const title = data.title || 'Waiting The Longest';
    const options = {
        body: data.body || 'New animals need your help!',
        icon: '/images/icon-192x192.png',
        badge: '/images/badge-72x72.png',
        vibrate: [200, 100, 200],
        tag: data.tag || 'general',
        data: data.url || '/',
        actions: [
            {
                action: 'view',
                title: 'View Animals'
            },
            {
                action: 'close',
                title: 'Close'
            }
        ]
    };

    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

/**
 * Notification click handler
 */
self.addEventListener('notificationclick', (event) => {
    console.log('[Service Worker] Notification clicked:', event.action);

    event.notification.close();

    if (event.action === 'view' || !event.action) {
        const urlToOpen = event.notification.data || '/';

        event.waitUntil(
            clients.matchAll({ type: 'window', includeUncontrolled: true })
                .then((clientList) => {
                    // Check if there's already a window open
                    for (const client of clientList) {
                        if (client.url === urlToOpen && 'focus' in client) {
                            return client.focus();
                        }
                    }
                    // Open new window
                    if (clients.openWindow) {
                        return clients.openWindow(urlToOpen);
                    }
                })
        );
    }
});

/**
 * Message handler for communication with main thread
 */
self.addEventListener('message', (event) => {
    console.log('[Service Worker] Message received:', event.data);

    if (event.data.action === 'skipWaiting') {
        self.skipWaiting();
    }

    if (event.data.action === 'clearCache') {
        event.waitUntil(
            caches.keys().then((cacheNames) => {
                return Promise.all(
                    cacheNames.map((name) => caches.delete(name))
                );
            })
        );
    }
});

console.log('[Service Worker] Loaded successfully', CACHE_VERSION);
