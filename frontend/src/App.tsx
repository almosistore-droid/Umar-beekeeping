import { useState } from 'react'
import { RouterProvider } from 'react-router-dom'
import { LoadingView, MessageView } from './components/StateViews'
import { useAuth } from './hooks/useAuth'
import { router } from './router'

export function AuthGate({ children }: { children: React.ReactNode }) {
  const { state, retry, loginWithInitData } = useAuth()
  switch (state.status) {
    case 'loading':
      return <LoadingView text="Вход через Telegram…" />
    case 'outside-telegram':
      return (
        <>
          <MessageView
            icon="🐝"
            title="Откройте в Telegram"
            text="Это приложение работает внутри Telegram. Откройте бота и нажмите «Открыть пасеку»."
          />
          {import.meta.env.DEV && <DevLogin onSubmit={loginWithInitData} />}
        </>
      )
    case 'error':
      return (
        <>
          <MessageView icon="⚠️" title="Не удалось войти" text={state.message} action={{ label: 'Повторить', onClick: retry }} />
          {import.meta.env.DEV && <DevLogin onSubmit={loginWithInitData} />}
        </>
      )
    case 'authenticated':
      return <>{children}</>
  }
}

export function App() {
  return (
    <AuthGate>
      <RouterProvider router={router} />
    </AuthGate>
  )
}

/**
 * Shown only in the local dev server (never in production builds).
 * The pasted string is a normally signed initData and goes through the same
 * server-side signature check as Telegram — this is not an auth bypass.
 */
function DevLogin({ onSubmit }: { onSubmit: (initData: string) => void }) {
  const [value, setValue] = useState('')
  return (
    <form className="card dev-login" onSubmit={(e) => { e.preventDefault(); if (value.trim()) onSubmit(value) }}>
      <h2 className="card__title">🧪 Вход для проверки на компьютере</h2>
      <p className="hint small">
        Выполните в папке проекта:<br />
        <code>docker compose -f docker-compose.dev.yml exec backend python -m app.utils.dev_init_data 111111</code><br />
        и вставьте результат сюда.
      </p>
      <textarea className="input" rows={3} value={value} onChange={(e) => setValue(e.target.value)}
        placeholder="auth_date=...&user=...&hash=..." aria-label="Строка входа" />
      <button className="btn btn--primary btn--block" type="submit">Войти</button>
    </form>
  )
}
