import { getLang, tr } from '../i18n'

/** Thin fetch wrapper: base URL, bearer token, readable Russian error messages. */

export class ApiError extends Error {
  status: number
  fieldErrors: { field: string; message: string }[]

  constructor(status: number, message: string, fieldErrors: { field: string; message: string }[] = []) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.fieldErrors = fieldErrors
  }
}

const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? ''

let accessToken: string | null = null
let onUnauthorized: (() => void) | null = null
let onPaymentRequired: (() => void) | null = null
let network: { failed: () => void; ok: () => void } | null = null

/** services/connection: learns from every request whether the server is reachable. */
export function setNetworkHandlers(handlers: { failed: () => void; ok: () => void } | null) {
  network = handlers
}

// Token is kept in memory only: on reload the app re-authenticates with fresh initData.
export function setAccessToken(token: string | null) {
  accessToken = token
}

export function hasAccessToken(): boolean {
  return accessToken !== null
}

export function setUnauthorizedHandler(handler: (() => void) | null) {
  onUnauthorized = handler
}

/** 402 = the subscription of this installation has ended: the app switches to the blocked screen. */
export function setPaymentRequiredHandler(handler: (() => void) | null) {
  onPaymentRequired = handler
}

const FALLBACK_MESSAGES: Record<number, string> = {
  401: tr("Требуется вход через Telegram"),
  403: tr("Недостаточно прав"),
  404: tr("Не найдено"),
  422: tr("Проверьте введённые данные"),
  429: tr("Слишком много запросов, попробуйте чуть позже"),
}

async function request(path: string, init: RequestInit): Promise<Response> {
  const headers = new Headers(init.headers)
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)
  headers.set('X-Lang', getLang()) // the server answers errors, reports and labels in this language

  let response: Response
  try {
    response = await fetch(`${BASE_URL}${path}`, { ...init, headers })
  } catch {
    network?.failed()
    throw new ApiError(0, tr("Нет соединения с сервером. Проверьте интернет."))
  }
  network?.ok()
  if (!response.ok) await raise(response)
  return response
}

async function raise(response: Response): Promise<never> {
  const data = await response.json().catch(() => null)
  const detail = typeof data?.detail === 'string' ? data.detail : null
  const message = detail ?? FALLBACK_MESSAGES[response.status] ?? tr("Ошибка сервера. Попробуйте позже.")
  if (response.status === 401 && accessToken) onUnauthorized?.()
  if (response.status === 402) onPaymentRequired?.()
  throw new ApiError(response.status, message, Array.isArray(data?.errors) ? data.errors : [])
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await request(path, init)
  if (response.status === 204) return undefined as T
  return (await response.json().catch(() => null)) as T
}

/** Binary response (PDF etc.) with the file name from Content-Disposition. */
export async function apiBlob(path: string, init: RequestInit = {}): Promise<{ blob: Blob; filename: string }> {
  const response = await request(path, init)
  const match = /filename="?([^";]+)"?/.exec(response.headers.get('Content-Disposition') ?? '')
  return { blob: await response.blob(), filename: match?.[1] ?? 'file' }
}
