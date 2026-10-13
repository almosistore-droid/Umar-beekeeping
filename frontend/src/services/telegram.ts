import type { TelegramWebApp } from '../types/telegram'

/** The Telegram WebApp object, or null when opened outside Telegram. */
export function getWebApp(): TelegramWebApp | null {
  const wa = window.Telegram?.WebApp
  // The SDK script defines WebApp even in a normal browser, but initData is empty there.
  return wa && wa.initData ? wa : null
}

/**
 * Signed initData to send to the backend. The backend verifies the signature;
 * the client never sends a bare user id.
 * In local development (vite dev server only) a pre-signed string from
 * VITE_DEV_INIT_DATA may be used to open the app in a normal browser.
 */
export function getInitData(): string | null {
  const wa = getWebApp()
  if (wa) return wa.initData
  if (import.meta.env.DEV && import.meta.env.VITE_DEV_INIT_DATA) {
    return import.meta.env.VITE_DEV_INIT_DATA as string
  }
  return null
}

export function isInsideTelegram(): boolean {
  return getWebApp() !== null
}

// The app uses the Fayzi Umar brand palette in every Telegram theme; Telegram's own
// header and background are painted to match so the Mini App looks seamless.
const BRAND_BG = '#15120c'

function paintTelegramChrome(wa: TelegramWebApp) {
  try {
    wa.setHeaderColor?.(BRAND_BG)
    wa.setBackgroundColor?.(BRAND_BG)
    if (wa.isVersionAtLeast('7.10')) wa.setBottomBarColor?.(BRAND_BG)
  } catch {
    /* older Telegram clients: keep their default colours */
  }
}

/** Call once at startup: tells Telegram we're ready, expands, syncs theme. */
export function initTelegram(): void {
  const wa = getWebApp()
  document.documentElement.dataset.theme = 'dark'
  if (!wa) return
  wa.ready()
  wa.expand()
  if (wa.isVersionAtLeast('7.7')) wa.disableVerticalSwipes?.()
  paintTelegramChrome(wa)
}

export function haptic(kind: 'light' | 'success' | 'error' = 'light'): void {
  const h = getWebApp()?.HapticFeedback
  if (!h) return
  if (kind === 'light') h.impactOccurred('light')
  else h.notificationOccurred(kind)
}
