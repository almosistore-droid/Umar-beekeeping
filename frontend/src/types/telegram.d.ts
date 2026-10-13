// Minimal typings for the official Telegram Mini Apps SDK (telegram-web-app.js)
// https://core.telegram.org/bots/webapps#initializing-mini-apps

export interface TelegramThemeParams {
  bg_color?: string
  text_color?: string
  hint_color?: string
  link_color?: string
  button_color?: string
  button_text_color?: string
  secondary_bg_color?: string
  header_bg_color?: string
  accent_text_color?: string
  section_bg_color?: string
  destructive_text_color?: string
}

export interface TelegramBackButton {
  isVisible: boolean
  show(): void
  hide(): void
  onClick(cb: () => void): void
  offClick(cb: () => void): void
}

export interface TelegramHaptic {
  impactOccurred(style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft'): void
  notificationOccurred(type: 'error' | 'success' | 'warning'): void
  selectionChanged(): void
}

export interface TelegramWebApp {
  initData: string
  initDataUnsafe: {
    user?: { id: number; first_name?: string; last_name?: string; username?: string }
    start_param?: string
  }
  version: string
  platform: string
  colorScheme: 'light' | 'dark'
  themeParams: TelegramThemeParams
  isExpanded: boolean
  ready(): void
  expand(): void
  close(): void
  isVersionAtLeast(version: string): boolean
  onEvent(event: string, cb: () => void): void
  offEvent(event: string, cb: () => void): void
  BackButton: TelegramBackButton
  HapticFeedback: TelegramHaptic
  disableVerticalSwipes?: () => void
  setHeaderColor?: (color: string) => void
  setBackgroundColor?: (color: string) => void
  setBottomBarColor?: (color: string) => void
  /** Bot API 6.4+: native QR scanner. Return true from the callback to close it. */
  showScanQrPopup?: (params: { text?: string }, callback?: (text: string) => boolean | void) => void
  closeScanQrPopup?: () => void
  openLink?: (url: string) => void
  openTelegramLink?: (url: string) => void
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp }
  }
}
