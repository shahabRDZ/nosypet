// NosyPet service worker.
// Strategy: cache the app shell (CSS/JS/icon) for offline use; pass
// every other request through to the network. The cache is keyed by
// version so a deploy invalidates old shells.
{% load static %}
const VERSION = "v1";
const SHELL = [
    "{% static 'pets/css/app.css' %}",
    "{% static 'pets/css/scene.css' %}",
    "{% static 'pets/js/dashboard.js' %}",
    "{% static 'favicon.svg' %}"
];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(VERSION).then((cache) => cache.addAll(SHELL))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k)))
        ).then(() => self.clients.claim())
    );
});

self.addEventListener("fetch", (event) => {
    const req = event.request;
    if (req.method !== "GET") return;
    // Never cache HTML or API responses — they are session-specific.
    const url = new URL(req.url);
    if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/admin/")) return;
    event.respondWith(
        caches.match(req).then((cached) => cached || fetch(req).catch(() => cached))
    );
});
