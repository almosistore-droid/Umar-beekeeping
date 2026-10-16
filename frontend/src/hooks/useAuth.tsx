import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { authApi } from '../api/auth'
import { ApiError, setAccessToken, setUnauthorizedHandler } from '../api/client'
import { clearDeviceToken, readDeviceToken, saveDeviceToken } from '../services/device'
import { getInitData } from '../services/telegram'
import type { AuthResponse, LoginPoll, User } from '../types/api'
import { adoptServerLang, tr } from '../i18n'

type AuthState =
  | { status: 'loading' }
  /** Outside Telegram and this phone is not logged in: show «Войти через Telegram». */
  | { status: 'signed-out'; message?: string }
  | { status: 'error'; message: string }
  | { status: 'authenticated'; user: User; startParam: string | null; via: 'telegram' | 'device' }

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
    setState({ status: 'authenticated', user: res.user, startParam: res.start_param ?? null, via })
    adoptServerLang(res.user.language) // chosen on another device
  }, [])

  const login = useCallback(async () => {
    if (inFlight.current) return
    const initData = getInitData() ?? manualInitData.current
    const deviceToken = initData ? null : readDeviceToken()
    if (!initData && !deviceToken) {
      setState({ status: 'signed-out' })
      return
    }
    inFlight.current = true
    setState({ status: 'loading' })
    try {
      if (initData) accept(await authApi.loginWithTelegram(initData), 'telegram')
      else accept(await authApi.loginWithDevice(deviceToken!), 'device')
    } catch (e) {
      setAccessToken(null)
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
      void login()
    })
    void login()
    return () => setUnauthorizedHandler(null)
  }, [login])

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
      retry: login,
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
