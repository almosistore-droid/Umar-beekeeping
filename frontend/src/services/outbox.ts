/**
 * Work without internet at the apiary.
 *
 * Inspections, feedings and treatments saved while the phone has no connection are kept here
 * (localStorage, survives closing the app) and sent in order when the connection is back.
 * Every record carries a `client_uid` made on the phone, so sending it twice (the answer was lost)
 * still creates one record on the server.
 */
import { useSyncExternalStore } from 'react'
import { ApiError, api, hasAccessToken } from '../api/client'

export type OutboxKind = 'inspection' | 'feeding' | 'treatment'

export interface OutboxItem {
  id: string            // = client_uid
  kind: OutboxKind
  hive_id: string
  hive_number: string | null
  path: string
  body: Record<string, unknown>
  created_at: string
  /** The server refused it (e.g. the hive was archived meanwhile): needs the person's decision. */
  error?: string | null
}

const KEY = 'fayzi-umar.outbox'
const listeners = new Set<() => void>()
let items: OutboxItem[] = load()
let online = typeof navigator === 'undefined' ? true : navigator.onLine !== false
let sending = false

function load(): OutboxItem[] {
  try {
    const raw = window.localStorage.getItem(KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function save() {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(items))
  } catch {
    /* storage full or blocked: the items stay in memory until the app is closed */
  }
  snapshot = { items, online, sending }
  listeners.forEach((fn) => fn())
}

let snapshot = { items, online, sending }

export function outboxSnapshot() {
  return snapshot
}

export function subscribeOutbox(fn: () => void): () => void {
  listeners.add(fn)
  return () => { listeners.delete(fn) }
}

export function useOutbox() {
  return useSyncExternalStore(subscribeOutbox, outboxSnapshot, outboxSnapshot)
}

export function newUid(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID()
  // older WebViews
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
  })
}

export function setOnline(value: boolean) {
  if (online === value) return
  online = value
  save()
}

export function enqueue(item: Omit<OutboxItem, 'created_at'>): OutboxItem {
  const full = { ...item, created_at: new Date().toISOString() }
  items = [...items.filter((i) => i.id !== item.id), full]
  save()
  return full
}

export function removeItem(id: string) {
  items = items.filter((i) => i.id !== id)
  save()
}

export function retryItem(id: string) {
  items = items.map((i) => (i.id === id ? { ...i, error: null } : i))
  save()
}

export type Queued = { queued: true; outboxId: string }
export const isQueued = (x: unknown): x is Queued => !!x && typeof x === 'object' && (x as Queued).queued === true

/**
 * Save a hive record: online — straight to the server; no connection — into the outbox.
 * The record gets its time now, so a record sent tomorrow keeps today's date.
 */
export async function saveOrQueue<T>(kind: OutboxKind, hive: { id: string; hive_number?: string | null }, path: string,
  body: Record<string, unknown>): Promise<T | Queued> {
  const withUid = { ...body, client_uid: (body.client_uid as string | undefined) ?? newUid() }
  const queue = (): Queued => {
    setOnline(false)
    enqueue({ id: withUid.client_uid as string, kind, hive_id: hive.id, hive_number: hive.hive_number ?? null, path, body: withUid })
    return { queued: true, outboxId: withUid.client_uid as string }
  }
  if (!online || (typeof navigator !== 'undefined' && navigator.onLine === false)) return queue()
  // one bar of signal: do not keep the beekeeper waiting — after 15 s the record goes to the outbox
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), 15_000)
  try {
    const res = await api<T>(path, { method: 'POST', body: JSON.stringify(withUid), signal: ctrl.signal })
    setOnline(true)
    return res
  } catch (e) {
    if (e instanceof ApiError && e.status === 0) return queue()
    throw e
  } finally {
    clearTimeout(timer)
  }
}

/**
 * Send what is waiting, oldest first. Stops at the first connection problem; a record the server refuses
 * (4xx) is marked with the reason and skipped. Returns how many were sent.
 */
export async function flushOutbox(onSent?: (item: OutboxItem) => void): Promise<number> {
  if (sending || !hasAccessToken()) return 0
  const pending = items.filter((i) => !i.error)
  if (!pending.length) return 0
  sending = true
  save()
  let sent = 0
  try {
    for (const item of pending) {
      try {
        await api(item.path, { method: 'POST', body: JSON.stringify(item.body) })
        setOnline(true)
        removeItem(item.id)
        sent += 1
        onSent?.(item)
      } catch (e) {
        if (!(e instanceof ApiError) || e.status === 0) { setOnline(false); break }
        if (e.status === 401 || e.status === 402 || e.status >= 500 || e.status === 429) break // try again later
        items = items.map((i) => (i.id === item.id ? { ...i, error: e.message } : i))
        save()
      }
    }
  } finally {
    sending = false
    save()
  }
  return sent
}

/** Test helper. */
export function resetOutbox() {
  items = []
  online = true
  sending = false
  save()
}
