import { Link } from 'react-router-dom'
import { Icon } from '../components/Icon'
import { useAuth } from '../hooks/useAuth'
import { usePermissions } from '../hooks/usePermissions'
import { ROLE_LABELS } from '../types/api'
import { useState } from 'react'
import { authApi } from '../api/auth'
import { Choice } from '../components/ui'
import { LANGS, getLang, switchLang, tr, type Lang } from '../i18n'

export function MorePage() {
  const { user } = useAuth()
  const { isAdmin, canManage } = usePermissions()
  if (!user) return null
  return (
    <div className="page">
      <h1 className="page__title">{tr("Ещё")}</h1>
      {isAdmin && (
        <nav className="menu">
          <Link to="/admin" className="menu__item"><Icon name="shield" />{tr("Админ-панель")}<span className="chevron">›</span></Link>
        </nav>
      )}
      <nav className="menu">
        {canManage && <Link to="/queens" className="menu__item"><Icon name="crown" />{tr("Матки")}<span className="chevron">›</span></Link>}
        <Link to="/apiaries" className="menu__item"><Icon name="apiary" />{tr("Пасеки")}<span className="chevron">›</span></Link>
        <Link to="/honey" className="menu__item"><Icon name="honey" />{tr("Мёд")}<span className="chevron">›</span></Link>
        <Link to="/products" className="menu__item"><Icon name="feed" />{tr("Продукция")}<span className="chevron">›</span></Link>
        <Link to="/qr-labels" className="menu__item"><Icon name="qr" />{tr("QR-наклейки")}<span className="chevron">›</span></Link>
        <Link to="/tasks" className="menu__item"><Icon name="treat" />{tr("Напоминания")}<span className="chevron">›</span></Link>
      </nav>
      <section className="card">
        <h2 className="card__title">{tr("Профиль")}</h2>
        <div className="row"><span className="hint">{tr("Имя")}</span><span>{user.display_name}</span></div>
        {user.username && <div className="row"><span className="hint">Telegram</span><span>@{user.username}</span></div>}
        <div className="row"><span className="hint">Telegram ID</span><span>{user.telegram_id}</span></div>
        <div className="row"><span className="hint">{tr("Роль")}</span><span>{ROLE_LABELS[user.role]}</span></div>
      </section>
      <LanguageCard />
    </div>
  )
}

/** Язык / Забон: saved on the device and the server, then the app reloads in the new language. */
function LanguageCard() {
  const [saving, setSaving] = useState(false)
  const choose = async (lang: Lang | null) => {
    if (!lang || lang === getLang() || saving) return
    setSaving(true)
    try {
      await authApi.setLanguage(lang)
    } catch {
      /* offline: the device still remembers the choice */
    }
    switchLang(lang)
  }
  return (
    <section className="card">
      <h2 className="card__title">Язык · Забон</h2>{/* i18n-ignore: always in both languages */}
      <Choice options={LANGS} value={getLang()} onChange={choose} />{/* i18n-ignore */}
    </section>
  )
}

