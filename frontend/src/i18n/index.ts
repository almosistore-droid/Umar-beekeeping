/**
 * Two languages: Русский (source) and Тоҷикӣ.
 *
 * The Russian text itself is the key: `tr('Сохранить осмотр')`. Placeholders are `{0}`, `{1}`…:
 * `tr('Улей №{0}', number)`. A missing Tajik translation falls back to Russian, and the coverage test
 * (src/test/i18n.test.ts) fails the build if any text used in the app is not translated.
 *
 * The language is fixed for a page load (module-level label maps are built once); switching the
 * language saves it and reloads the Mini App.
 */
import tg from './tg.json'

export type Lang = 'ru' | 'tg'
export const LANGS: { value: Lang; label: string }[] = [
  { value: 'ru', label: 'Русский' },
  { value: 'tg', label: 'Тоҷикӣ' },
]
const STORAGE_KEY = 'fayzi-umar.lang'
const catalogs: Record<Lang, Record<string, string>> = { ru: {}, tg: tg as Record<string, string> }

function telegramLanguage(): string | undefined {
  try {
    return window.Telegram?.WebApp?.initDataUnsafe?.user?.language_code
  } catch {
    return undefined
  }
}

function stored(): Lang | null {
  try {
    const v = window.localStorage.getItem(STORAGE_KEY)
    return v === 'ru' || v === 'tg' ? v : null
  } catch {
    return null
  }
}

/** Saved choice, else Telegram's language (tg → Тоҷикӣ), else Russian. */
export function detectLang(): Lang {
  const saved = stored()
  if (saved) return saved
  return telegramLanguage()?.toLowerCase().startsWith('tg') ? 'tg' : 'ru'
}

let current: Lang = detectLang()

export function getLang(): Lang {
  return current
}

/** Test helper: switch without reload. */
export function setLangForTests(lang: Lang): void {
  current = lang
}

// null / undefined render as nothing, like in JSX
const show = (v: unknown) => (v === null || v === undefined ? '' : String(v))

function fill(text: string, args: unknown[]): string {
  return args.length ? text.replace(/\{(\d+)\}/g, (m, i) => (Number(i) < args.length ? show(args[Number(i)]) : m)) : text
}

/** Translate a Russian UI text into the current language. */
export function tr(ru: string, ...args: unknown[]): string {
  const translated = current === 'ru' ? ru : catalogs[current][ru] ?? ru
  return fill(translated, args)
}

/** Saves the choice on the device and reloads so every screen is rebuilt in the new language. */
export function switchLang(lang: Lang, reload: () => void = () => window.location.reload()): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, lang)
  } catch {
    /* private mode: the choice lasts until the page is closed */
  }
  current = lang
  reload()
}

/** Apply a language saved on the server (another device) when nothing is saved locally. */
export function adoptServerLang(lang: Lang | null | undefined, reload: () => void = () => window.location.reload()): void {
  if (!lang || stored() || lang === current) return
  switchLang(lang, reload)
}
