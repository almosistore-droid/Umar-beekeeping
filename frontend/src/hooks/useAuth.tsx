import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { authApi } from '../api/auth'
import { ApiError, setAccessToken, setUnauthorizedHandler } from '../api/client'
import { clearDeviceToken, readDeviceToken, saveDeviceToken } from '../services/device'
import { getInitData } from '../services/telegram'
import type { AuthResponse, LoginPoll, User } from '../types/api'
import { adoptServerLang, tr } from '../i18n'
import { forgetCache } from '../services/offlineCache'
import { flushOutbox, subscribeOutbox, outboxSnapshot } from '../services/outbox'

const USER_KEY = 'fayzi-umar.user'

function rememberUser(user: User) {
  try { window.localStorage.setItem(USER_KEY, JSON.stringify(user)) } catch { /* private mode */ }
}

function rememberedUser(): User | null {
  try {
    const raw = window.localStorage.getItem(USER_KEY)
    return raw ? (JSON.parse(raw) as User) : null
  } catch {
    return null
  }
}

function forgetUser() {
  try { window.localStorage.removeItem(USER_KEY) } catch { /* nothing */ }
}

type AuthState =
  | { status: 'loading' }
  /** Outside Telegram and this phone is not logged in: show «Войти через Telegram». */
  | { status: 'signed-out'; message?: string }
  | { status: 'error'; message: string }
  /** `offline`: opened at the apiary without internet with the last profile; the server is asked again later. */
  | { status: 'authenticated'; user: User; startParam: string | null; via: 'telegram' | 'device'; offline?: boolean }

interface AuthContextValue {
  state: AuthState
  user: User | null
  /** Logged in on the phone app (outside Telegram): «Выйти» is available. */
  onDevice: boolean
  retry: () => void
  /** The bot confirmed the login on this phone. */
  completeDeviceLogin: (result: LoginPoll) => void
  logout: () => Promise<void>
  /** The profile changed on the server (e.g. the temporary password was replaced). */
  updateUser: (user: User) => void
  /** Local testing only: log in with a signed initData string pasted by the developer. */
  loginWithInitData: (initData: string) => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: 'loading' })
  const inFlight = useRef(false)
  const manualInitData = useRef<string | null>(null)

  const accept = useCallback((res: AuthResponse, via: 'telegram' | 'device') => {
    setAccessToken(res.access_token)
    setState((s) => ({
      status: 'authenticated', user: res.user, via,
      // a silent re-login after the connection returned keeps the screen where it is
      startParam: s.status === 'authenticated' && s.offline ? null : res.start_param ?? null,
    }))
    rememberUser(res.user)
    adoptServerLang(res.user.language) // chosen on another device
    void flushOutbox()
  }, [])

  const login = useCallback(async (silent = false) => {
    if (inFlight.current) return
    const initData = getInitData() ?? manualInitData.current
    const deviceToken = initData ? null : readDeviceToken()
    if (!initData && !deviceToken) {
      setState({ status: 'signed-out' })
      return
    }
    inFlight.current = true
    if (!silent) setState({ status: 'loading' })
    try {
      if (initData) accept(await authApi.loginWithTelegram(initData), 'telegram')
      else accept(await authApi.loginWithDevice(deviceToken!), 'device')
    } catch (e) {
      setAccessToken(null)
      const cached = rememberedUser()
      if (e instanceof ApiError && e.status === 0 && cached) {
        // At the apiary without internet: open with the last profile; saving goes to the outbox
        setState({ status: 'authenticated', user: cached, startParam: null, via: initData ? 'telegram' : 'device', offline: true })
        return
      }
      const message = e instanceof ApiError ? e.message : tr("Не удалось войти")
      if (!initData && e instanceof ApiError && (e.status === 401 || e.status === 403)) {
        clearDeviceToken() // logged out elsewhere, expired or blocked: ask to log in again
        setState({ status: 'signed-out', message })
      } else {
        setState({ status: 'error', message })
      }
    } finally {
      inFlight.current = false
    }
  }, [accept])

  useEffect(() => {
    // Session expired mid-use: silently re-login (same initData or the device token)
    setUnauthorizedHandler(() => {
      setAccessToken(null)
      void login(true)
    })
    void login()
    return () => setUnauthorizedHandler(null)
  }, [login])

  // Opened offline: when the connection is back, log in quietly (then the outbox is sent)
  const offline = state.status === 'authenticated' && !!state.offline
  useEffect(() => {
    if (!offline) return
    return subscribeOutbox(() => { if (outboxSnapshot().online) void login(true) })
  }, [offline, login])

  const completeDeviceLogin = useCallback((result: LoginPoll) => {
    if (result.status !== 'ok' || !result.access_token || !result.device_token || !result.user) return
    saveDeviceToken(result.device_token)
    accept({ access_token: result.access_token, token_type: 'bearer', expires_in: result.expires_in ?? 0,
      user: result.user, start_param: null }, 'device')
  }, [accept])

  const logout = useCallback(async () => {
    const token = readDeviceToken()
    clearDeviceToken()
    if (token) await authApi.logout(token).catch(() => { /* offline: the token is forgotten on this phone anyway */ })
    setAccessToken(null)
    forgetUser()
    await forgetCache()
    setState({ status: 'signed-out' })
  }, [])

  const updateUser = useCallback((user: User) => {
    setState((s) => (s.status === 'authenticated' ? { ...s, user } : s))
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      state,
      user: state.status === 'authenticated' ? state.user : null,
      onDevice: state.status === 'authenticated' && state.via === 'device',
      retry: () => { void login() },
      completeDeviceLogin,
      logout,
      updateUser,
      loginWithInitData: (initData: string) => {
        manualInitData.current = initData.trim()
        void login()
      },
    }),
    [state, login, completeDeviceLogin, logout, updateUser],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
