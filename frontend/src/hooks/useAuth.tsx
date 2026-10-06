import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { authApi } from '../api/auth'
import { ApiError, setAccessToken, setUnauthorizedHandler } from '../api/client'
import { getInitData } from '../services/telegram'
import type { User } from '../types/api'

type AuthState =
  | { status: 'loading' }
  | { status: 'outside-telegram' }
  | { status: 'error'; message: string }
  | { status: 'authenticated'; user: User; startParam: string | null }

interface AuthContextValue {
  state: AuthState
  user: User | null
  retry: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: 'loading' })
  const inFlight = useRef(false)

  const login = useCallback(async () => {
    if (inFlight.current) return
    const initData = getInitData()
    if (!initData) {
      setState({ status: 'outside-telegram' })
      return
    }
    inFlight.current = true
    setState({ status: 'loading' })
    try {
      const res = await authApi.loginWithTelegram(initData)
      setAccessToken(res.access_token)
      setState({ status: 'authenticated', user: res.user, startParam: res.start_param })
    } catch (e) {
      setAccessToken(null)
      setState({ status: 'error', message: e instanceof ApiError ? e.message : 'Не удалось войти' })
    } finally {
      inFlight.current = false
    }
  }, [])

  useEffect(() => {
    // Session expired mid-use: silently re-login with the same initData
    setUnauthorizedHandler(() => {
      setAccessToken(null)
      void login()
    })
    void login()
    return () => setUnauthorizedHandler(null)
  }, [login])

  const value = useMemo<AuthContextValue>(
    () => ({ state, user: state.status === 'authenticated' ? state.user : null, retry: login }),
    [state, login],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
