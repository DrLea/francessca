// Francesca service worker: makes the site installable and lets the app
// shell — above all the offline assistant at /offline — open with no
// network. It never touches the API: user data is not cached here.

const VERSION = "v2";
const CACHE = `francessca-shell-${VERSION}`;
const PRECACHE = [
  "/",
  "/offline",
  "/manifest.webmanifest",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/brand/mark.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      // One by one, so a single missing URL does not fail the install.
      .then((cache) => Promise.all(PRECACHE.map((url) => cache.add(url).catch(() => {}))))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key.startsWith("francessca-shell-") && key !== CACHE)
            .map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

// A page can hand over the URLs of the scripts and styles it loaded, so
// that exact page works offline next time (see /offline).
self.addEventListener("message", (event) => {
  const data = event.data || {};
  if (data.type !== "CACHE_URLS" || !Array.isArray(data.urls)) return;
  const urls = data.urls.filter(
    (url) => typeof url === "string" && new URL(url, self.location.origin).origin === self.location.origin,
  );
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => Promise.all(urls.map((url) => cache.add(url).catch(() => {})))),
  );
});

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) (await caches.open(CACHE)).put(request, response.clone());
  return response;
}

async function networkFirst(request, isNavigation) {
  try {
    const response = await fetch(request);
    if (response.ok) (await caches.open(CACHE)).put(request, response.clone());
    return response;
  } catch (error) {
    const cached =
      (await caches.match(request)) ||
      (isNavigation && (await caches.match(request, { ignoreSearch: true })));
    if (cached) return cached;
    if (isNavigation) {
      // No copy of that page: the offline assistant still works.
      const offline = (await caches.match("/offline")) || (await caches.match("/offline/"));
      if (offline) return offline;
    }
    throw error;
  }
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  // Other origins (the API, the model weights) and the same-origin API of
  // the desktop build are left entirely to the browser.
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/") || url.pathname === "/sw.js") return;

  if (url.pathname.startsWith("/_next/static/") || url.pathname.startsWith("/icons/")) {
    // Content-hashed by the build, so a cached copy is never stale.
    event.respondWith(cacheFirst(request));
    return;
  }
  event.respondWith(networkFirst(request, request.mode === "navigate"));
});
