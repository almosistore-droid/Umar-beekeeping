/**
 * Brand of this installation (each subscriber has their own copy of the app with their own name,
 * logo and colour). Loaded once from the public GET /api/branding before the app renders; if the
 * server can't be reached the app keeps the built-in defaults and the usual «Нет соединения» flow.
 */
import { useSyncExternalStore } from 'react'
import { api } from '../api/client'

export type Subscription = { active: boolean; days_left: number | null; contact: string | null }

export type Branding = {
  name: string
  subtitle: string
  color: string
  color_light: string
  color_deep: string
  logo_url: string
  icon_url: string
  subscription: Subscription
  /** false: users, roles and the activity log are managed only in the subscription owner's panel */
  admin_in_app?: boolean
}

export const DEFAULT_BRANDING: Branding = {
  name: 'Fayzi Umar',
  subtitle: 'Учёт пасеки', // i18n-ignore: replaced by the server's (translated) subtitle
  color: '#f4c23b',
  color_light: '#ffd65a',
  color_deep: '#c98e17',
  logo_url: '/api/branding/logo.png',
  icon_url: '/api/branding/icon-180.png',
  subscription: { active: true, days_left: null, contact: null },
  admin_in_app: true,
}

const BRAND_KEY = 'fayzi-umar.brand'
let current: Branding = DEFAULT_BRANDING
const listeners = new Set<() => void>()

export function getBranding(): Branding {
  return current
}

export function subscribeBranding(fn: () => void): () => void {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

function setBranding(next: Branding) {
  current = next
  applyBranding(next)
  listeners.forEach((fn) => fn())
}

/** «r, g, b» for rgba() shadows in styles.css. */
export function hexToRgb(hex: string): string {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex.trim())
  if (!m) return '244, 194, 59'
  const n = parseInt(m[1], 16)
  return `${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}`
}

export function applyBranding(b: Branding) {
  const root = document.documentElement.style
  root.setProperty('--gold', b.color)
  root.setProperty('--gold-light', b.color_light)
  root.setProperty('--gold-deep', b.color_deep)
  root.setProperty('--gold-rgb', hexToRgb(b.color))
  document.title = b.name
  document.querySelector('meta[name="apple-mobile-web-app-title"]')?.setAttribute('content', b.name)
}

function valid(data: unknown): data is Branding {
  const d = data as Branding | null
  return !!d && typeof d.name === 'string' && typeof d.color === 'string' && !!d.subscription
}

/** Called before the first render; never throws and never waits longer than `timeoutMs`. */
export async function loadBranding(timeoutMs = 4000): Promise<Branding> {
  const timeout = new Promise<null>((resolve) => setTimeout(() => resolve(null), timeoutMs))
  const data = await Promise.race([api<unknown>('/api/branding').catch(() => null), timeout])
  if (valid(data)) {
    try { window.localStorage.setItem(BRAND_KEY, JSON.stringify(data)) } catch { /* private mode */ }
    setBranding(data)
  } else {
    // no connection at the apiary: the brand seen last time (the subscription is checked again online)
    let saved: unknown = null
    try { saved = JSON.parse(window.localStorage.getItem(BRAND_KEY) ?? 'null') } catch { /* broken */ }
    setBranding(valid(saved) ? { ...saved, subscription: { ...saved.subscription, active: true } } : DEFAULT_BRANDING)
  }
  return current
}

/** The server answered 402: the subscription ran out while the app was open. */
export function markSubscriptionEnded() {
  if (!current.subscription.active) return
  setBranding({ ...current, subscription: { ...current.subscription, active: false, days_left: 0 } })
}

/** React hook: re-renders when the brand or the subscription state changes. */
export function useBranding(): Branding {
  return useSyncExternalStore(subscribeBranding, getBranding, getBranding)
}
