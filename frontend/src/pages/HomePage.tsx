import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { useAuth } from '../hooks/useAuth'
import { ROLE_LABELS } from '../types/api'

export function HomePage() {
  const { user } = useAuth()
  const health = useQuery({
    queryKey: ['health'],
    queryFn: () => api<{ status: string; database: string }>('/api/health'),
  })

  return (
    <div className="page">
      <header className="page__header">
        <p className="hint">Добро пожаловать</p>
        <h1 className="page__title">{user?.display_name ?? 'Пчеловод'} 🐝</h1>
        {user && <span className="chip">{ROLE_LABELS[user.role]}</span>}
      </header>

      <section className="card">
        <h2 className="card__title">Состояние системы</h2>
        <div className="row">
          <span>Сервер и база данных</span>
          <span className={health.data?.status === 'ok' ? 'ok' : 'warn'}>
            {health.isLoading ? '…' : health.data?.status === 'ok' ? '🟢 Работает' : '🔴 Недоступно'}
          </span>
        </div>
        <div className="row">
          <span>Вход через Telegram</span>
          <span className="ok">🟢 Подтверждён</span>
        </div>
      </section>

      <section className="card card--muted">
        <h2 className="card__title">Сводка пасеки</h2>
        <p className="hint">
          Здесь появятся ульи, матки, сила семей, мёд и финансы после подключения модулей
          пасек и ульев (этап 2) и статистики (этап 6).
        </p>
      </section>
    </div>
  )
}
