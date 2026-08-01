const CACHE_NAME = "inventorypro-v5"; // Incremented version to clear old cache layers
const FILES_TO_CACHE = [
    "/",
    "/static/inventory/css/bootstrap.min.css",
    "/static/inventory/offline-db.js",
    "/static/inventory/product-loader.js",
    "/static/inventory/network.js"
];

// Installation Lifecycle - Cache static system dependencies
self.addEventListener("install", event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                return cache.addAll(FILES_TO_CACHE);
            })
    );
    self.skipWaiting();
});

// Activation Lifecycle - Purge stale cache structures automatically
self.addEventListener("activate", event => {
    event.waitUntil(
        caches.keys()
            .then(keys => {
                return Promise.all(
                    keys.map(key => {
                        if (key !== CACHE_NAME) {
                            return caches.delete(key);
                        }
                    })
                );
            })
    );
    self.clients.claim();
});

// Fetch Interception Engine - Safe offline routing matrix
self.addEventListener("fetch", event => {
    const url = new URL(event.request.url);

    // 1. BYPASS RULE: Direct network bypass for Bootstrap CDN or external assets
    if (url.hostname.includes("cdn.jsdelivr.net") || !url.origin.includes(self.location.hostname)) {
        return; // Let the browser handle external requests over the real network
    }

    // 2. BYPASS RULE: Do not intercept asynchronous dynamic backend search API points
    if (url.pathname.includes("/search/")) {
        return; // Allow the AJAX search script to hit your real Django views directly
    }

    // 3. CACHE STRATEGY: Standard Progressive Web App response mapping
    event.respondWith(
        caches.match(event.request)
            .then(cachedResponse => {
                if (cachedResponse) {
                    return cachedResponse; // Return matching static asset instantly
                }

                return fetch(event.request)
                    .catch(() => {
                        // Safe offline fallback rules: only route page navigations to root
                        if (event.request.mode === 'navigate') {
                            return caches.match("/");
                        }
                    });
            })
    );
});
