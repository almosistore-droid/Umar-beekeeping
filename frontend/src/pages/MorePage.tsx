import { Link } from 'react-router-dom'
import { Icon } from '../components/Icon'
import { useAuth } from '../hooks/useAuth'
import { usePermissions } from '../hooks/usePermissions'
import { ROLE_LABELS } from '../types/api'
import { useState } from 'react'
import { authApi } from '../api/auth'
import { notificationsApi } from '../api/resources'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getWebApp, haptic } from '../services/telegram'
import { Choice, Sheet } from '../components/ui'
import { ChangePasswordForm } from '../components/auth/PasswordForms'
import { InstallHint } from '../components/auth/InstallHint'
import { isStandalone } from '../services/pwa'
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
        <Link to="/stock" className="menu__item"><Icon name="box" />{tr("Склад")}<span className="chevron">›</span></Link>
        <Link to="/honey" className="menu__item"><Icon name="honey" />{tr("Мёд")}<span className="chevron">›</span></Link>
        <Link to="/products" className="menu__item"><Icon name="feed" />{tr("Продукция")}<span className="chevron">›</span></Link>
        <Link to="/qr-labels" className="menu__item"><Icon name="qr" />{tr("QR-наклейки")}<span className="chevron">›</span></Link>
        <Link to="/tasks" className="menu__item"><Icon name="treat" />{tr("Напоминания")}<span className="chevron">›</span></Link>
      </nav>
      <section className="card">
        <h2 className="card__title">{tr("Профиль")}</h2>
        <div className="row"><span className="hint">{tr("Имя")}</span><span>{user.display_name}</span></div>
        {user.username && <div className="row"><span className="hint">Telegram</span><span>@{user.username}</span></div>}
        {user.telegram_id && <div className="row"><span className="hint">Telegram ID</span><span>{user.telegram_id}</span></div>}
        {user.login && <div className="row"><span className="hint">{tr("Логин")}</span><span>{user.login}</span></div>}
        <div className="row"><span className="hint">{tr("Роль")}</span><span>{ROLE_LABELS[user.role]}</span></div>
        {user.has_password && <PasswordButton />}
      </section>
      <nav className="menu">
        <Link to="/stock/norms" className="menu__item"><Icon name="edit" />{tr("Нормы расхода: рамки и корм")}<span className="chevron">›</span></Link>
      </nav>
      <NotificationsCard />
      <LanguageCard />
      <PhoneAppCard />
    </div>
  )
}

/**
 * The app on the phone's home screen. In Telegram: open the address in the phone's browser to install it.
 * In the installed app / a browser: install hint and «Выйти».
 */
function PhoneAppCard() {
  const { onDevice, logout } = useAuth()
  const [leaving, setLeaving] = useState(false)
  const wa = getWebApp()
  if (wa) {
    if (!wa.openLink) return null
    return (
      <section className="card">
        <h2 className="card__title">{tr("Приложение на телефоне")}</h2>
        <p className="hint small">{tr("Можно открывать пасеку значком на главном экране, без Telegram. Откройте адрес в браузере телефона и установите приложение; вход — через этого же бота.")}</p>
        <button type="button" className="btn btn--secondary btn--block" onClick={() => wa.openLink?.(window.location.origin + '/')}>
          <Icon name="mobile" size={18} />{tr("Открыть в браузере")}
        </button>
      </section>
    )
  }
  if (isStandalone() && !onDevice) return null
  return (
    <section className="card">
      <h2 className="card__title">{tr("Приложение на телефоне")}</h2>
      <InstallHint />
      {onDevice && (
        <button type="button" className="btn btn--ghost btn--block" disabled={leaving}
          onClick={() => { setLeaving(true); void logout() }}>
          <Icon name="logout" size={18} />{tr("Выйти на этом устройстве")}
        </button>
      )}
    </section>
  )
}

/** Stage 8: reminders in Telegram, each as its own message; apiary work and CRM can be turned off. */
function NotificationsCard() {
  const qc = useQueryClient()
  const settings = useQuery({ queryKey: ['notification-settings'], queryFn: notificationsApi.settings })
  const update = useMutation({
    mutationFn: notificationsApi.update,
    onSuccess: (s) => { haptic('light'); qc.setQueryData(['notification-settings'], s) },
  })
  const test = useMutation({ mutationFn: notificationsApi.test, onSuccess: () => haptic('success'), onError: () => haptic('error') })
  const s = settings.data
  if (!s) return null
  return (
    <section className="card">
      <h2 className="card__title">{tr("Напоминания в Telegram")}</h2>
      {!s.telegram ? (
        <p className="hint small">{tr("Напоминания приходят в Telegram, а у вас вход без Telegram. Смотрите их в «Ещё → Напоминания».")}</p>
      ) : (
        <>
          <p className="hint small">{tr("Каждое напоминание приходит отдельным сообщением от бота (в {0}).", s.hours)}</p>
          <label className="switch">
            <input type="checkbox" checked={s.field} disabled={update.isPending} onChange={(e) => update.mutate({ field: e.target.checked })} />
            <span>{tr("Работа на пасеке: осмотры, обработки, подкормки, матки, зимовка")}</span>
          </label>
          {s.crm_available && (
            <label className="switch">
              <input type="checkbox" checked={s.crm} disabled={update.isPending} onChange={(e) => update.mutate({ crm: e.target.checked })} />
              <span>{tr("CRM: долги клиентов и заказы")}</span>
            </label>
          )}
          {test.isSuccess && <p className="ok-box small" role="status">{tr("Отправлено — проверьте чат с ботом.")}</p>}
          {test.error instanceof Error && <p className="error-box" role="alert">{test.error.message}</p>}
          <button type="button" className="btn btn--ghost btn--block" disabled={test.isPending} onClick={() => test.mutate()}>
            <Icon name="send" size={18} />{tr("Прислать пробное сообщение")}
          </button>
        </>
      )}
    </section>
  )
}

function PasswordButton() {
  const [open, setOpen] = useState(false)
  const [done, setDone] = useState(false)
  return (
    <>
      {done && <p className="ok-box small" role="status">{tr("Пароль изменён.")}</p>}
      <button type="button" className="btn btn--ghost btn--block" onClick={() => { setDone(false); setOpen(true) }}>
        <Icon name="shield" size={18} />{tr("Сменить пароль")}
      </button>
      <Sheet open={open} title={tr("Сменить пароль")} onClose={() => setOpen(false)}>
        {open && <ChangePasswordForm onDone={() => { setOpen(false); setDone(true) }} />}
      </Sheet>
    </>
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

