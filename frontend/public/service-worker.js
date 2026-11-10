/* Service worker Ruang Baca SMANSA
 * - Halaman (navigasi): network-first, cadangan ke app shell yang tersimpan.
 * - Aset statis ber-hash (build produksi): cache-first.
 * - Aset statis lain (gambar, font, bundle dev): stale-while-revalidate / network-first.
 * - Data API GET (katalog buku, rak, pengaturan, dll): network-first, cadangan cache saat offline.
 * - Login, logout, unggah, unduh berkas, cadangan & pemulihan TIDAK pernah di-cache.
 * - Halaman admin (/admin: Sirkulasi, Pengunjung, Laporan Pengunjung) & portal siswa disimpan saat install
 *   sehingga tetap bisa dibuka tanpa internet. Data offline (antrean) disimpan aplikasi di IndexedDB.
 * Ubah VERSION untuk memaksa pembaruan cache.
 */
const VERSION = "v4";
const SHELL_CACHE = `perpus-shell-${VERSION}`;
const STATIC_CACHE = `perpus-static-${VERSION}`;
const IMG_CACHE = `perpus-img-${VERSION}`;
const API_CACHE = `perpus-api-${VERSION}`;
const KNOWN = [SHELL_CACHE, STATIC_CACHE, IMG_CACHE, API_CACHE];

const SHELL_KEY = "/";
const PRECACHE = [
  "/",
  "/admin",
  "/siswa",
  "/fonts/fonts.css",
  "/fonts/Shrikhand-400.woff2",
  "/fonts/Orbitron-var.woff2",
  "/fonts/ChakraPetch-400.woff2",
  "/fonts/ChakraPetch-600.woff2",
  "/fonts/ChakraPetch-700.woff2",
  "/fonts/Rajdhani-400.woff2",
  "/fonts/Rajdhani-600.woff2",
  "/fonts/Rajdhani-700.woff2",
  "/fonts/Exo2-var.woff2",
  "/fonts/Audiowide-400.woff2",
  "/offline.html",
  "/manifest.json",
  "/logo-sekolah.png",
  "/logo-perpustakaan.png",
  "/favicon.ico",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/apple-touch-icon.png",
];

const NAV_TIMEOUT = 4000;
const API_TIMEOUT = 8000;
const LIMITS = { [STATIC_CACHE]: 120, [IMG_CACHE]: 400, [API_CACHE]: 220 };

// API yang tidak boleh disimpan (sensitif, berkas unduhan, atau aksi admin)
const API_BYPASS = /\/api\/(auth\/(login|logout)|admin\/|uploads\/|reports\/purge|restore)|\.(pdf|xlsx|xls|zip|csv)(\?|$)|import-template/i;
// Permintaan dev server / hot reload
const DEV_BYPASS = /(hot-update|sockjs-node|__webpack|\/ws$|webpack-dev-server)/i;
const HASHED = /\.[0-9a-f]{8,}(\.chunk)?\.(js|css)$/i;
const IMAGE_EXT = /\.(png|jpe?g|gif|webp|svg|ico|avif)$/i;
const FONT_EXT = /\.(woff2?|ttf|otf|eot)$/i;
const THIRD_PARTY_SKIP = /(^|\.)emergent\.sh$|posthog|google-analytics|googletagmanager/i;

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(SHELL_CACHE);
    await Promise.all(PRECACHE.map(async (url) => {
      try {
        const res = await fetch(url, { cache: "reload" });
        if (!res.ok) return;
        const isPage = url === "/" || url === "/admin" || url === "/siswa";
        await (isPage || url.startsWith("/fonts/") ? caches.open(isPage ? SHELL_CACHE : STATIC_CACHE) : Promise.resolve(cache)).then((c) => c.put(url, res.clone()));
        if (url === "/") await precacheShellAssets(await res.text());
      } catch (e) { /* abaikan, akan dicoba lagi saat runtime */ }
    }));
    await precacheBuildChunks();
  })());
});

// Build produksi: simpan semua bundle ber-hash (termasuk halaman yang dimuat terpisah) agar kunjungan berikutnya instan
async function precacheBuildChunks() {
  try {
    const res = await fetch("/asset-manifest.json", { cache: "no-store" });
    if (!res.ok) return;
    const files = Object.values((await res.json()).files || {}).filter((f) => typeof f === "string" && HASHED.test(f) && !f.endsWith(".map"));
    const cache = await caches.open(STATIC_CACHE);
    await Promise.all(files.map(async (f) => { try { if (!(await cache.match(f))) { const r = await fetch(f); if (r.ok) await cache.put(f, r); } } catch (e) { /* */ } }));
  } catch (e) { /* dev server: tidak ada manifest */ }
}

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k.startsWith("perpus-") && !KNOWN.includes(k)).map((k) => caches.delete(k)));
    if (self.registration.navigationPreload) { try { await self.registration.navigationPreload.enable(); } catch (e) { /* */ } }
    await self.clients.claim();
  })());
});

self.addEventListener("message", (event) => {
  const msg = event.data || {};
  if (msg.type === "SKIP_WAITING") self.skipWaiting();
  if (msg.type === "CLEAR_API_CACHE") event.waitUntil(caches.delete(API_CACHE));
  if (msg.type === "WARM" && Array.isArray(msg.urls)) event.waitUntil(warm(msg.urls));
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  let url;
  try { url = new URL(req.url); } catch (e) { return; }
  if (!url.protocol.startsWith("http")) return;
  if (THIRD_PARTY_SKIP.test(url.hostname)) return;
  const sameOrigin = url.origin === self.location.origin;

  // Data API (bisa same-origin atau domain backend terpisah)
  if (url.pathname.startsWith("/api/")) {
    if (API_BYPASS.test(url.pathname + url.search)) return;
    if (req.headers.get("range")) return;
    // Permintaan "fresh" (mis. cek server sudah normal) -> selalu ke jaringan, jangan pakai cache
    if (req.headers.get("x-perpus-fresh") || url.searchParams.has("fresh")) return;
    if (url.pathname.startsWith("/api/files/")) { event.respondWith(staleWhileRevalidate(req, IMG_CACHE, event)); return; }
    // Sampul buku ber-versi (?v=) -> tidak berubah, simpan permanen di HP
    if (/^\/api\/books\/[^/]+\/cover$/.test(url.pathname)) { event.respondWith(url.searchParams.get("v") ? cacheFirst(req, IMG_CACHE) : staleWhileRevalidate(req, IMG_CACHE, event)); return; }
    event.respondWith(apiNetworkFirst(req, event));
    return;
  }

  if (sameOrigin) {
    if (DEV_BYPASS.test(url.pathname) || url.pathname.startsWith("/__")) return;
    if (req.mode === "navigate") { event.respondWith(navigationHandler(event)); return; }
    if (url.pathname === "/service-worker.js") return;
    if (HASHED.test(url.pathname)) { event.respondWith(cacheFirst(req, STATIC_CACHE)); return; }
    if (IMAGE_EXT.test(url.pathname) || FONT_EXT.test(url.pathname)) { event.respondWith(staleWhileRevalidate(req, STATIC_CACHE, event)); return; }
    if (/\.(js|css|json|map)$/i.test(url.pathname)) { event.respondWith(networkFirst(req, STATIC_CACHE, 6000)); return; }
    return;
  }

  // Font Google & gambar QR / sampul eksternal
  if (/fonts\.(googleapis|gstatic)\.com$/.test(url.hostname)) { event.respondWith(staleWhileRevalidate(req, STATIC_CACHE, event)); return; }
  if (url.hostname === "api.qrserver.com") { event.respondWith(cacheFirst(req, IMG_CACHE)); return; }
  if (req.destination === "image") { event.respondWith(staleWhileRevalidate(req, IMG_CACHE, event)); return; }
});

/* ---------------- Strategi ---------------- */

function timeout(ms) { return new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), ms)); }

async function navigationHandler(event) {
  const cache = await caches.open(SHELL_CACHE);
  const network = (async () => {
    const preload = await event.preloadResponse;
    const res = preload || await fetch(event.request);
    if (res && res.ok && (res.headers.get("content-type") || "").includes("text/html")) {
      const path = new URL(event.request.url).pathname;
      event.waitUntil(Promise.all([cache.put(SHELL_KEY, res.clone()), path !== "/" ? cache.put(path, res.clone()) : null]));
    }
    return res;
  })();
  try {
    return await Promise.race([network, timeout(NAV_TIMEOUT)]);
  } catch (e) {
    const shell = (await cache.match(new URL(event.request.url).pathname)) || await cache.match(SHELL_KEY);
    if (shell) { event.waitUntil(network.catch(() => {})); return shell; }
    try { return await network; } catch (err) { return (await cache.match("/offline.html")) || Response.error(); }
  }
}

async function cacheFirst(req, cacheName) {
  const cache = await caches.open(cacheName);
  const hit = await cache.match(req);
  if (hit) return hit;
  const res = await fetch(req);
  if (res && (res.ok || res.type === "opaque")) { await cache.put(req, res.clone()); trim(cacheName); }
  return res;
}

async function networkFirst(req, cacheName, ms) {
  const cache = await caches.open(cacheName);
  try {
    const res = await Promise.race([fetch(req), timeout(ms)]);
    if (res && res.ok) { cache.put(req, res.clone()); trim(cacheName); }
    return res;
  } catch (e) {
    const hit = await cache.match(req);
    if (hit) return hit;
    return fetch(req);
  }
}

async function staleWhileRevalidate(req, cacheName, event) {
  const cache = await caches.open(cacheName);
  const hit = await cache.match(req);
  const update = fetch(req).then((res) => {
    if (res && (res.ok || res.type === "opaque")) { cache.put(req, res.clone()); trim(cacheName); }
    return res;
  }).catch(() => null);
  if (hit) { if (event) event.waitUntil(update); return hit; }
  const res = await update;
  return res || Response.error();
}

async function apiNetworkFirst(req, event) {
  const cache = await caches.open(API_CACHE);
  const network = fetch(req).then(async (res) => {
    const type = res.headers.get("content-type") || "";
    if (res.ok && type.includes("application/json")) {
      const body = await res.clone().blob();
      const headers = new Headers(res.headers);
      headers.set("x-sw-cached-at", new Date().toISOString());
      await cache.put(req, new Response(body, { status: res.status, statusText: res.statusText, headers }));
      trim(API_CACHE);
    }
    return res;
  });
  try {
    return await Promise.race([network, timeout(API_TIMEOUT)]);
  } catch (e) {
    const hit = await cache.match(req, { ignoreVary: true });
    if (hit) {
      event.waitUntil(network.catch(() => {}));
      return markFromCache(hit);
    }
    try { return await network; } catch (err) {
      return new Response(JSON.stringify({ detail: "Sedang offline. Data ini belum pernah dimuat sebelumnya, sambungkan internet lalu coba lagi." }), {
        status: 503, statusText: "Offline", headers: { "Content-Type": "application/json", "x-sw-offline": "1" },
      });
    }
  }
}

async function markFromCache(res) {
  const body = await res.blob();
  const headers = new Headers(res.headers);
  headers.set("x-sw-cache", "hit");
  return new Response(body, { status: res.status, statusText: res.statusText, headers });
}

async function precacheShellAssets(html) {
  const urls = new Set();
  const re = /(?:src|href)="(\/[^"]+\.(?:js|css|png|ico|json))"/g;
  let m;
  while ((m = re.exec(html))) urls.add(m[1]);
  await warm([...urls]);
}

async function warm(urls) {
  const cache = await caches.open(STATIC_CACHE);
  await Promise.all(urls.slice(0, 80).map(async (u) => {
    try {
      const url = new URL(u, self.location.origin);
      const font = /fonts\.(googleapis|gstatic)\.com$/.test(url.hostname);
      if (font) {
        if (await cache.match(url.href)) return;
        const res = await fetch(url.href, { mode: "cors", credentials: "omit" });
        if (res.ok) await cache.put(url.href, res);
        return;
      }
      if (url.origin !== self.location.origin || url.pathname.startsWith("/api/") || url.pathname.startsWith("/__") || DEV_BYPASS.test(url.pathname)) return;
      if (!/\.[a-z0-9]{2,5}$/i.test(url.pathname)) return; // hanya berkas statis, halaman ditangani app shell
      if (await cache.match(url.href)) return;
      const res = await fetch(url.href, { credentials: "same-origin" });
      if (res.ok) await cache.put(url.href, res);
    } catch (e) { /* abaikan */ }
  }));
  trim(STATIC_CACHE);
}

async function trim(cacheName) {
  const max = LIMITS[cacheName];
  if (!max) return;
  try {
    const cache = await caches.open(cacheName);
    const keys = await cache.keys();
    if (keys.length > max) await Promise.all(keys.slice(0, keys.length - max).map((k) => cache.delete(k)));
  } catch (e) { /* */ }
}
