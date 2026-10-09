import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { usePermissions } from '../hooks/usePermissions'
import { ROLE_LABELS } from '../types/api'

export function MorePage() {
  const { user } = useAuth()
  const { isAdmin } = usePermissions()
  if (!user) return null
  return (
    <div className="page">
      <h1 className="page__title">Ещё</h1>
      <nav className="menu">
        <Link to="/apiaries" className="menu__item"><span>🏡</span>Пасеки<span className="chevron">›</span></Link>
        {isAdmin && <Link to="/users" className="menu__item"><span>👥</span>Пользователи<span className="chevron">›</span></Link>}
      </nav>
      <section className="card">
        <h2 className="card__title">Профиль</h2>
        <div className="row"><span className="hint">Имя</span><span>{user.display_name}</span></div>
        {user.username && <div className="row"><span className="hint">Telegram</span><span>@{user.username}</span></div>}
        <div className="row"><span className="hint">Telegram ID</span><span>{user.telegram_id}</span></div>
        <div className="row"><span className="hint">Роль</span><span>{ROLE_LABELS[user.role]}</span></div>
      </section>
    </div>
  )
}
