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

// Token is kept in memory only: on reload the app re-authenticates with fresh initData.
export function setAccessToken(token: string | null) {
  accessToken = token
}

export function setUnauthorizedHandler(handler: (() => void) | null) {
  onUnauthorized = handler
}

const FALLBACK_MESSAGES: Record<number, string> = {
  401: 'Требуется вход через Telegram',
  403: 'Недостаточно прав',
  404: 'Не найдено',
  422: 'Проверьте введённые данные',
  429: 'Слишком много запросов, попробуйте чуть позже',
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)

  let response: Response
  try {
    response = await fetch(`${BASE_URL}${path}`, { ...init, headers })
  } catch {
    throw new ApiError(0, 'Нет соединения с сервером. Проверьте интернет.')
  }

  if (response.status === 204) return undefined as T

  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = typeof data?.detail === 'string' ? data.detail : null
    const message = detail ?? FALLBACK_MESSAGES[response.status] ?? 'Ошибка сервера. Попробуйте позже.'
    if (response.status === 401 && accessToken) onUnauthorized?.()
    throw new ApiError(response.status, message, Array.isArray(data?.errors) ? data.errors : [])
  }
  return data as T
}
