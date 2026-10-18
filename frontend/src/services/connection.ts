/**
 * Is the server reachable? `navigator.onLine` is not enough at the apiary (one bar of signal, no data),
 * so a failed request marks the app offline and a light ping to /api/health brings it back.
 * TanStack Query pauses fetching while offline (cached data stays on screen), and the outbox sends the
 * saved records when the connection returns.
 */
import { onlineManager } from '@tanstack/react-query'
import { setNetworkHandlers } from '../api/client'
import { outboxSnapshot, setOnline } from './outbox'

const PING_EVERY_MS = 15_000
let timer: ReturnType<typeof setInterval> | null = null
let backOnline: (() => void) | null = null

async function ping(): Promise<boolean> {
  try {
    const res = await fetch('/api/health', { cache: 'no-store' })
    return res.ok
  } catch {
    return false
  }
}

export function markOffline() {
  if (!outboxSnapshot().online && timer) return
  setOnline(false)
  onlineManager.setOnline(false)
  if (!timer) timer = setInterval(() => { void ping().then((ok) => ok && markOnline()) }, PING_EVERY_MS)
}

export function markOnline() {
  if (timer) { clearInterval(timer); timer = null }
  const was = outboxSnapshot().online
  setOnline(true)
  onlineManager.setOnline(true)
  if (!was) backOnline?.()
}

/** Call once at startup; `onBack` runs when the connection returns (sends the outbox). */
export function initConnection(onBack: () => void) {
  backOnline = onBack
  onlineManager.setEventListener(() => () => undefined) // we decide, not only the browser events
  setNetworkHandlers({ failed: markOffline, ok: () => { if (!outboxSnapshot().online) markOnline() } })
  window.addEventListener('offline', markOffline)
  window.addEventListener('online', () => { void ping().then((ok) => (ok ? markOnline() : markOffline())) })
  if (navigator.onLine === false) markOffline()
}
