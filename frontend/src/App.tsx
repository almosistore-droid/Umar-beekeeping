import { RouterProvider } from 'react-router-dom'
import { LoadingView, MessageView } from './components/StateViews'
import { useAuth } from './hooks/useAuth'
import { router } from './router'

export function AuthGate({ children }: { children: React.ReactNode }) {
  const { state, retry } = useAuth()
  switch (state.status) {
    case 'loading':
      return <LoadingView text="Вход через Telegram…" />
    case 'outside-telegram':
      return (
        <MessageView
          icon="🐝"
          title="Откройте в Telegram"
          text="Это приложение работает внутри Telegram. Откройте бота и нажмите «Открыть пасеку»."
        />
      )
    case 'error':
      return <MessageView icon="⚠️" title="Не удалось войти" text={state.message} action={{ label: 'Повторить', onClick: retry }} />
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
