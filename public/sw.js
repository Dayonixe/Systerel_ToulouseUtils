const CACHE_NAME = "le-hub-toulouse-v1";
const APP_SHELL = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./favicon.svg",
  "./icons/apple-touch-icon.png",
  "./icons/pwa-192x192.png",
  "./icons/pwa-512x512.png",
  "./icons/pwa-maskable-512x512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(APP_SHELL))
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
            .filter((key) => key !== CACHE_NAME)
            .map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") {
    return;
  }

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) {
    return;
  }

  // Les offres et l’état de synchronisation doivent toujours venir du réseau.
  if (url.pathname.includes("/data/") && url.pathname.endsWith(".json")) {
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then(async (response) => {
          if (response.ok) {
            const cache = await caches.open(CACHE_NAME);
            await cache.put("./", response.clone());
          }
          return response;
        })
        .catch(async () => {
          const cached = await caches.match("./");
          return cached ?? Response.error();
        }),
    );
    return;
  }

  if (!["script", "style", "image", "font"].includes(request.destination)) {
    return;
  }

  const refresh = fetch(request).then(async (response) => {
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      await cache.put(request, response.clone());
    }
    return response;
  });
  event.waitUntil(refresh.catch(() => undefined));
  event.respondWith(
    caches.match(request).then((cached) => cached ?? refresh),
  );
});
