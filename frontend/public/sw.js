/* Service worker: makes the app installable and opens it quickly.
 * Caches only the static app (HTML shell, hashed /assets/, fonts) and the brand images (/api/branding/*).
 * Never other /api answers: the app keeps its own offline copy of the data (services/offlineCache).
 * The HTML is fetched from the network first, so a new release shows up on the next launch. */
const CACHE = 'beekeeping-v3'
// Icons and the manifest are served by the backend (/api/branding/…) with the installation's brand
const SHELL = ['/']

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()))
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (event) => {
  const req = event.request
  if (req.method !== 'GET') return
  const url = new URL(req.url)
  if (url.origin !== self.location.origin) return
  if (url.pathname.startsWith('/api/branding/')) {
    // logo, icons, manifest: public and rarely changed — from the cache at once, refreshed in the background
    event.respondWith(caches.open(CACHE).then((c) => c.match(req).then((hit) => {
      const fresh = fetch(req).then((res) => { if (res.ok) c.put(req, res.clone()); return res }).catch(() => hit)
      return hit || fresh
    })))
    return
  }
  if (url.pathname.startsWith('/api/')) return // data is never cached here (the app keeps its own copy)

  if (req.mode === 'navigate') {
    // network first; offline → the cached shell (the app then shows «Нет соединения»)
    event.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone()
          caches.open(CACHE).then((c) => c.put('/', copy))
          return res
        })
        .catch(() => caches.match('/')),
    )
    return
  }

  if (url.pathname.startsWith('/assets/')) {
    // file names contain a content hash: cache forever
    event.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((res) => {
        if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)) }
        return res
      })),
    )
  }
})
