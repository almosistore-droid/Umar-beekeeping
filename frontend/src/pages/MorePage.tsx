import { useAuth } from '../hooks/useAuth'
import { ROLE_LABELS } from '../types/api'

export function MorePage() {
  const { user } = useAuth()
  if (!user) return null
  return (
    <div className="page">
      <h1 className="page__title">Профиль</h1>
      <section className="card">
        <div className="row"><span className="hint">Имя</span><span>{user.display_name}</span></div>
        {user.username && (
          <div className="row"><span className="hint">Telegram</span><span>@{user.username}</span></div>
        )}
        <div className="row"><span className="hint">Telegram ID</span><span>{user.telegram_id}</span></div>
        <div className="row"><span className="hint">Роль</span><span>{ROLE_LABELS[user.role]}</span></div>
      </section>
    </div>
  )
}
