const CACHE_NAME = "inventorypro-v17"; // Bumped version structure layer
const FILES_TO_CACHE = [
    "/",
    "/static/inventory/css/bootstrap.min.css",
    "/static/inventory/css/bootstrap-icons.min.css",
    "/static/inventory/css/fonts/bootstrap-icons.woff",
    "/static/inventory/css/fonts/bootstrap-icons.woff2",
    "/static/inventory/offline-db.js",
    "/static/inventory/product-loader.js",
    "/static/inventory/network.js",
    "/static/inventory/js/bootstrap.bundle.min.js",
    "/static/inventory/js/dashboard.js",
    "/static/inventory/js/search.js"
];

self.addEventListener("install", event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(FILES_TO_CACHE))
    );
    self.skipWaiting();
});

self.addEventListener("activate", event => {
    event.waitUntil(
        caches.keys().then(keys => Promise.all(
            keys.map(key => {
                if (key !== CACHE_NAME) return caches.delete(key);
            })
        ))
    );
    self.clients.claim();
});

self.addEventListener("fetch", event => {
    const url = new URL(event.request.url);

    // 1. BYPASS RULE: External resource handling execution safety block
    if (url.hostname.includes("cdn.jsdelivr.net") || !url.origin.includes(self.location.hostname)) {
        return;
    }

    // 2. BYPASS RULE: Dynamic search matching prevents worker interception duplication
    if (url.pathname.includes("search")) {
        return;
    }

    // 3. Only intercept and cache GET requests
    if (event.request.method !== "GET") {
        return;
    }

    // 4. CACHE STRATEGY: Serve from cache first, refresh in the background.
    //    Pages and static assets are cached as they are visited online.
    event.respondWith(
        caches.match(event.request).then(cachedResponse => {
            const network = fetch(event.request)
                .then(response => {
                    if (response && response.status === 200 && response.type === "basic") {
                        const copy = response.clone();
                        caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
                    }
                    return response;
                })
                .catch(() => {
                    if (event.request.mode === 'navigate') {
                        return caches.match("/");
                    }
                });

            return cachedResponse || network;
        })
    );
});
