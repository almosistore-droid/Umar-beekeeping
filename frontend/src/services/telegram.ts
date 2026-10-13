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

/** Native QR scanner is available (Telegram 6.4+ on a phone or desktop with a camera). */
export function canScanQr(): boolean {
  const wa = getWebApp()
  return !!wa?.showScanQrPopup && wa.isVersionAtLeast('6.4')
}

/**
 * Opens Telegram's camera scanner; calls onResult once with the first text read and closes.
 * Returns false when the scanner is not available (outside Telegram).
 */
export function scanQr(text: string, onResult: (value: string) => void): boolean {
  const wa = getWebApp()
  if (!wa?.showScanQrPopup || !canScanQr()) return false
  let done = false
  wa.showScanQrPopup({ text }, (value) => {
    if (done) return true
    done = true
    haptic('success')
    onResult(value)
    return true
  })
  return true
}

let startParamUsed = false

/**
 * The deep-link payload (t.me/<bot>/<app>?startapp=…) the Mini App was opened with.
 * Returned only once per page load so going back does not re-open the same hive.
 */
export function takeStartParam(): string | null {
  if (startParamUsed) return null
  startParamUsed = true
  const fromSdk = getWebApp()?.initDataUnsafe.start_param
  if (fromSdk) return fromSdk
  const search = new URLSearchParams(window.location.search)
  const hash = new URLSearchParams(window.location.hash.replace(/^#/, ''))
  return search.get('tgWebAppStartParam') ?? hash.get('tgWebAppStartParam') ?? null
}

/** Test helper. */
export function resetStartParamForTests(): void {
  startParamUsed = false
}

/**
 * Share a text message: Telegram's «send to a chat» picker inside the Mini App,
 * the system share sheet or the clipboard elsewhere. Returns how it was shared.
 */
export async function shareText(text: string): Promise<'telegram' | 'system' | 'copied' | 'none'> {
  const wa = getWebApp()
  if (wa?.openTelegramLink) {
    wa.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(text)}`)
    return 'telegram'
  }
  try {
    if (navigator.share) { await navigator.share({ text }); return 'system' }
    await navigator.clipboard.writeText(text)
    return 'copied'
  } catch {
    return 'none'
  }
}
