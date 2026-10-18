/**
 * Data the field work needs is kept on the phone (IndexedDB), so hives open without a connection:
 * hive list and passports, last inspections (to prefill frames), diseases, warehouse, apiaries, reminders.
 * Money (dashboard, CRM) is not stored. The cache belongs to one person: another login starts empty.
 */
import type { Query, QueryClient } from '@tanstack/react-query'
import { createAsyncStoragePersister } from '@tanstack/query-async-storage-persister'
import { del, get, set } from 'idb-keyval'
import { healthApi, hivesApi, stockApi } from '../api/resources'

const IDB_KEY = 'fayzi-umar.cache'
const USER_KEY = 'fayzi-umar.user'
const PREFETCH_KEY = 'fayzi-umar.prefetched'
export const CACHE_MAX_AGE = 14 * 24 * 3600 * 1000
const PERSISTED = new Set(['hive', 'hives', 'hive-inspections', 'hive-cases', 'diseases', 'stock', 'apiaries', 'tasks'])

export const persister = createAsyncStoragePersister({
  storage: { getItem: (k) => get(k), setItem: (k, v) => set(k, v), removeItem: (k) => del(k) },
  key: IDB_KEY,
  throttleTime: 2000,
})

export const shouldPersist = (q: Query) => q.state.status === 'success' && PERSISTED.has(String(q.queryKey[0]))

/** The last signed-in person (profile only, no token): lets the app open at the apiary without internet. */
export function cachedUserId(): string {
  try {
    const raw = window.localStorage.getItem(USER_KEY)
    return raw ? (JSON.parse(raw).id ?? '') : ''
  } catch {
    return ''
  }
}

export async function forgetCache() {
  try {
    window.localStorage.removeItem(PREFETCH_KEY)
    await del(IDB_KEY)
  } catch {
    /* nothing stored */
  }
}

/**
 * While online, load every working hive into the cache (at most every 6 hours), so a hive never opened
 * before still opens at the apiary. Small apiaries only (≤ 300 hives).
 */
export async function prefetchForOffline(qc: QueryClient, force = false) {
  try {
    const last = Number(window.localStorage.getItem(PREFETCH_KEY) ?? 0)
    if (!force && Date.now() - last < 6 * 3600 * 1000) return
    const list = await qc.fetchQuery({ queryKey: ['hives', 'offline-all'], queryFn: () => hivesApi.list({ limit: 300 }) })
    await Promise.all([
      qc.prefetchQuery({ queryKey: ['diseases'], queryFn: healthApi.diseases }),
      qc.prefetchQuery({ queryKey: ['stock', false], queryFn: () => stockApi.overview() }),
      qc.prefetchQuery({ queryKey: ['stock'], queryFn: () => stockApi.overview() }),
    ])
    const ids = list.items.filter((h) => !h.is_archived).map((h) => h.id)
    let i = 0
    const worker = async () => {
      while (i < ids.length) {
        const id = ids[i++]
        await qc.prefetchQuery({ queryKey: ['hive', id], queryFn: () => hivesApi.get(id) })
        await qc.prefetchQuery({ queryKey: ['hive-inspections', id], queryFn: () => healthApi.inspections(id) })
      }
    }
    await Promise.all([worker(), worker(), worker()])
    window.localStorage.setItem(PREFETCH_KEY, String(Date.now()))
  } catch {
    /* offline or a server problem: try next time */
  }
}
