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

const THEME_VARS: Record<string, string> = {
  bg_color: '--tg-bg',
  text_color: '--tg-text',
  hint_color: '--tg-hint',
  link_color: '--tg-link',
  button_color: '--tg-button',
  button_text_color: '--tg-button-text',
  secondary_bg_color: '--tg-secondary-bg',
  section_bg_color: '--tg-section-bg',
  destructive_text_color: '--tg-destructive',
  accent_text_color: '--tg-accent',
}

function applyTheme(wa: TelegramWebApp) {
  const root = document.documentElement
  root.dataset.theme = wa.colorScheme
  for (const [key, cssVar] of Object.entries(THEME_VARS)) {
    const value = wa.themeParams[key as keyof typeof wa.themeParams]
    if (value) root.style.setProperty(cssVar, value)
  }
}

/** Call once at startup: tells Telegram we're ready, expands, syncs theme. */
export function initTelegram(): void {
  const wa = getWebApp()
  if (!wa) {
    document.documentElement.dataset.theme =
      window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    return
  }
  wa.ready()
  wa.expand()
  if (wa.isVersionAtLeast('7.7')) wa.disableVerticalSwipes?.()
  applyTheme(wa)
  wa.onEvent('themeChanged', () => applyTheme(wa))
}

export function haptic(kind: 'light' | 'success' | 'error' = 'light'): void {
  const h = getWebApp()?.HapticFeedback
  if (!h) return
  if (kind === 'light') h.impactOccurred('light')
  else h.notificationOccurred(kind)
}
