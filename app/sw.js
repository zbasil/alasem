/* sw.js: makes the app installable and usable offline.
   - the page and icons: network first, cached copy when offline
   - data files: the network first, so an update is never hidden behind an old copy; the last copy only offline
   - the StatsBomb archive (never changes): the cached copy at once, refreshed in the background
   The build (scripts/build_app.py) replaces __BUILD__ so a new version drops old caches. */
const VERSION = "__BUILD__";
const SHELL = "zsc-shell-" + VERSION;
const DATA = "zsc-data-" + VERSION;
const SHELL_FILES = ["./", "index.html", "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png", "icons/icon.svg"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(SHELL).then((c) => c.addAll(SHELL_FILES)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k.startsWith("zsc-") && k !== SHELL && k !== DATA).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

function stripQuery(req) { const u = new URL(req.url); u.search = ""; return u.toString(); }

async function networkFirst(req, cacheName) {
  const key = stripQuery(req);
  try {
    const res = await fetch(req);
    if (res.ok) (await caches.open(cacheName)).put(key, res.clone());
    return res;
  } catch (err) {
    const hit = await caches.match(key);
    if (hit) return hit;
    throw err;
  }
}
async function staleWhileRevalidate(req) {
  const key = stripQuery(req);
  const cache = await caches.open(DATA);
  const hit = await cache.match(key);
  const net = fetch(req).then((res) => { if (res.ok) cache.put(key, res.clone()); return res; }).catch(() => null);
  return hit || (await net) || Response.error();
}

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;           // fonts and the live proxy go straight to the network
  if (url.pathname.includes("/api/")) return;                // the local server's API is never cached
  if (req.mode === "navigate") { e.respondWith(networkFirst(req, SHELL)); return; }
  if (url.pathname.includes("/data/")) {
    if (url.pathname.includes("/data/archive/")) e.respondWith(staleWhileRevalidate(req));
    else e.respondWith(networkFirst(req, DATA));
    return;
  }
  e.respondWith(networkFirst(req, SHELL));
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const target = (e.notification.data && e.notification.data.url) || "./";
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
    for (const c of list) { if ("focus" in c) { c.navigate(target).catch(() => {}); return c.focus(); } }
    return self.clients.openWindow(target);
  }));
});
