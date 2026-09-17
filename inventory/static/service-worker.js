const CACHE_NAME = "inventorypro-v24";
const OFFLINE_FALLBACK = "/static/offline.html";
const FILES_TO_CACHE = [
    "/static/offline.html",
    "/static/inventory/css/bootstrap.min.css",
    "/static/inventory/css/bootstrap-icons.min.css",
    "/static/inventory/css/fonts/bootstrap-icons.woff",
    "/static/inventory/css/fonts/bootstrap-icons.woff2",
    "/static/inventory/offline-db.js",
    "/static/inventory/product-loader.js",
    "/static/inventory/network.js",
    "/static/inventory/js/bootstrap.bundle.min.js",
    "/static/inventory/js/dashboard.js",
    "/static/inventory/js/search.js",
    "/static/inventory/js/pdfjs/pdf.min.js",
    "/static/inventory/js/pdfjs/pdf.worker.min.js"
];

self.addEventListener("install", event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache =>
            Promise.all(
                FILES_TO_CACHE.map(url =>
                    fetch(url, { credentials: "same-origin" })
                        .then(resp => {
                            if (resp && resp.status === 200) {
                                return cache.put(url, resp);
                            }
                        })
                        .catch(() => {})
                )
            ).then(() => self.skipWaiting())
        )
    );
});

self.addEventListener("activate", event => {
    event.waitUntil(
        caches.keys().then(keys => Promise.all(
            keys.map(key => {
                if (key !== CACHE_NAME) return caches.delete(key);
            })
        )).then(() => self.clients.claim())
    );
});

self.addEventListener("fetch", event => {
    const url = new URL(event.request.url);

    if (url.hostname.includes("cdn.jsdelivr.net") || !url.origin.includes(self.location.hostname)) {
        return;
    }

    if (event.request.method !== "GET") {
        return;
    }

    // API data: network-first, cache the response for offline use
    if (url.pathname === "/offline-products/") {
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    if (response && response.status === 200) {
                        const copy = response.clone();
                        caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
                    }
                    return response;
                })
                .catch(() => caches.match(event.request))
        );
        return;
    }

    // Pages: network-first, fall back to offline page
    if (event.request.mode === "navigate") {
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    if (response && response.status === 200 && response.type === "basic") {
                        const copy = response.clone();
                        caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
                    }
                    return response;
                })
                .catch(() =>
                    caches.match(event.request).then(cached =>
                        cached || caches.match(OFFLINE_FALLBACK)
                    )
                )
        );
        return;
    }

    // Static assets: cache-first, refresh in background
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
                .catch(() => undefined);

            return cachedResponse || network;
        })
    );
});
