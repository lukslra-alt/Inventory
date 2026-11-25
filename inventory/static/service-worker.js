const CACHE_NAME = "inventorypro-v26";
const OFFLINE_FALLBACK = "/static/offline.html";
const FILES_TO_CACHE = [
    "/static/offline.html",
    "/static/manifest.json",
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

// iOS/WebKit rejects any response handed to event.respondWith() (or stored with
// cache.put()) whose underlying fetch() followed an HTTP redirect, even when the
// final response is a normal 200 ("response served by service worker has
// redirections"). This app frequently redirects: "/" bounces to /accounts/login/
// when the session is missing/expired, and to /customers/ for non-staff users.
// Rebuild a clean Response so the redirected flag (and now-meaningless encoding
// headers) are dropped. Chromium does not need this, so the bug only shows on iOS.
function stripRedirect(response) {
    if (!response || !response.redirected) {
        return response;
    }
    if (response.status === 204 || response.status === 205 || response.status === 304) {
        return response;
    }
    try {
        const headers = new Headers(response.headers);
        headers.delete("content-encoding");
        headers.delete("content-length");
        headers.delete("transfer-encoding");
        return new Response(response.body, {
            status: response.status,
            statusText: response.statusText,
            headers: headers
        });
    } catch (error) {
        return response;
    }
}

async function putInCache(request, response) {
    const cache = await caches.open(CACHE_NAME);
    await cache.put(request, response);
}

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

    // Only handle our own origin; let the browser deal with everything else.
    if (url.origin !== self.location.origin) {
        return;
    }

    if (event.request.method !== "GET") {
        return;
    }

    // API data: network-first, cache the response for offline use.
    if (url.pathname === "/offline-products/") {
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    const clean = stripRedirect(response);
                    if (clean && clean.status === 200) {
                        const copy = clean.clone();
                        putInCache(event.request, copy).catch(() => {});
                    }
                    return clean;
                })
                .catch(() => caches.match(event.request))
        );
        return;
    }

    // Pages: network-first, fall back to cache then the offline page.
    if (event.request.mode === "navigate") {
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    const clean = stripRedirect(response);
                    if (clean && clean.status === 200 && clean.type === "basic") {
                        const copy = clean.clone();
                        putInCache(event.request, copy).catch(() => {});
                    }
                    return clean;
                })
                .catch(() =>
                    caches.match(event.request).then(cached =>
                        cached || caches.match(OFFLINE_FALLBACK)
                    )
                )
        );
        return;
    }

    // Static assets: cache-first, refresh in the background.
    event.respondWith(
        caches.match(event.request).then(cachedResponse => {
            const network = fetch(event.request)
                .then(response => {
                    const clean = stripRedirect(response);
                    if (clean && clean.status === 200 && clean.type === "basic") {
                        const copy = clean.clone();
                        putInCache(event.request, copy).catch(() => {});
                    }
                    return clean;
                })
                .catch(() => undefined);

            return cachedResponse || network;
        })
    );
});
