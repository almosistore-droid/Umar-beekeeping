/**
 * The app installed on the phone (outside Telegram).
 *
 * After the user confirms the login in the bot, the server gives this phone a device token. It is kept in
 * localStorage so the next launch opens straight away; it is revocable («Выйти», blocking the user) and is
 * exchanged for the usual short-lived access token, which stays in memory only.
 */
const KEY = 'fayzi-umar.device'

export function readDeviceToken(): string | null {
  try {
    return localStorage.getItem(KEY)
  } catch {
    return null
  }
}

export function saveDeviceToken(token: string): void {
  try {
    localStorage.setItem(KEY, token)
  } catch {
    /* private mode: the user logs in again next time */
  }
}

export function clearDeviceToken(): void {
  try {
    localStorage.removeItem(KEY)
  } catch {
    /* nothing to clear */
  }
}

/** «iPhone · Safari», «Android · Chrome» — shown in the bot and the activity log. */
export function deviceName(ua: string = navigator.userAgent): string {
  const os = /iPhone/.test(ua) ? 'iPhone' : /iPad/.test(ua) ? 'iPad' : /Android/.test(ua) ? 'Android'
    : /Windows/.test(ua) ? 'Windows' : /Mac OS X/.test(ua) ? 'Mac' : /Linux/.test(ua) ? 'Linux' : ''
  const browser = /YaBrowser/.test(ua) ? 'Yandex' : /SamsungBrowser/.test(ua) ? 'Samsung' : /Edg\//.test(ua) ? 'Edge'
    : /Firefox|FxiOS/.test(ua) ? 'Firefox' : /Chrome|CriOS/.test(ua) ? 'Chrome' : /Safari/.test(ua) ? 'Safari' : ''
  return [os, browser].filter(Boolean).join(' · ').slice(0, 120)
}
