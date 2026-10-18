import { lazy, Suspense, type ComponentType } from 'react'
import { LoadingView } from '../components/StateViews'

/**
 * Screens used less often (reports, CRM, admin, warehouse…) load on first open, so the app starts faster.
 * While online all of them are loaded in the background (`warmUpPages`) — the service worker keeps them,
 * and they open at the apiary without internet too.
 */
const loaders: (() => Promise<unknown>)[] = []
const RELOAD_KEY = 'fayzi-umar.chunk-reload'

function withReload<T>(load: () => Promise<T>): () => Promise<T> {
  return () => load().catch((e) => {
    // a new version was deployed and the old file names are gone: reload once to get the new ones
    try {
      if (!sessionStorage.getItem(RELOAD_KEY)) {
        sessionStorage.setItem(RELOAD_KEY, '1')
        window.location.reload()
      }
    } catch { /* storage blocked */ }
    throw e
  })
}

export function lazyPage<M extends Record<string, unknown>, K extends keyof M & string>(load: () => Promise<M>, name: K) {
  const safe = withReload(load)
  loaders.push(safe)
  const Page = lazy(() => safe().then((m) => ({ default: m[name] as ComponentType })))
  return <Suspense fallback={<LoadingView />}><Page /></Suspense>
}

export function warmUpPages() {
  try { sessionStorage.removeItem(RELOAD_KEY) } catch { /* storage blocked */ }
  const run = () => { for (const load of loaders) void load().catch(() => undefined) }
  const idle = (window as Window & { requestIdleCallback?: (cb: () => void) => void }).requestIdleCallback
  if (idle) idle(run)
  else setTimeout(run, 2000)
}
