import { useState, type FormEvent } from 'react'
import { useMutation } from '@tanstack/react-query'
import { authApi } from '../../api/auth'
import { useAuth } from '../../hooks/useAuth'
import { deviceName } from '../../services/device'
import { haptic, shareText } from '../../services/telegram'
import type { AccountCredentials } from '../../types/api'
import { Icon } from '../Icon'
import { ErrorBox, Field, SubmitButton } from '../ui'
import { tr } from '../../i18n'

/** Login + password for people without Telegram (accounts made by the admin). */
export function PasswordLoginForm() {
  const { completeDeviceLogin } = useAuth()
  const [login, setLogin] = useState('')
  const [password, setPassword] = useState('')
  const save = useMutation({
    mutationFn: () => authApi.passwordLogin(login.trim(), password, deviceName()),
    onSuccess: (res) => { haptic('success'); completeDeviceLogin(res) },
    onError: () => haptic('error'),
  })
  return (
    <form className="form login__form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate() }}>
      <ErrorBox error={save.error} />
      <Field label={tr("Логин")}>
        <input className="input input--big" value={login} onChange={(e) => setLogin(e.target.value)} autoComplete="username"
          autoCapitalize="off" autoCorrect="off" spellCheck={false} required />
      </Field>
      <Field label={tr("Пароль")}>
        <input className="input input--big" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password" required />
      </Field>
      <SubmitButton pending={save.isPending}>{tr("Войти")}</SubmitButton>
    </form>
  )
}

/** Change the password: forced after a temporary one from the admin, or any time from «Ещё». */
export function ChangePasswordForm({ forced = false, onDone }: { forced?: boolean; onDone?: () => void }) {
  const { user, updateUser } = useAuth()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [repeat, setRepeat] = useState('')
  const [local, setLocal] = useState<string | null>(null)
  const save = useMutation({
    mutationFn: () => authApi.changePassword(current, next),
    onSuccess: (u) => { haptic('success'); updateUser(u); onDone?.() },
    onError: () => haptic('error'),
  })
  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (next.length < 8) return setLocal(tr("Пароль должен быть не короче 8 символов"))
    if (next !== repeat) return setLocal(tr("Пароли не совпадают"))
    setLocal(null)
    save.mutate()
  }
  return (
    <form className="form" onSubmit={submit}>
      {local ? <div className="error-box" role="alert">{local}</div> : <ErrorBox error={save.error} />}
      {user?.login && <input type="text" value={user.login} autoComplete="username" readOnly hidden />}
      <Field label={forced ? tr("Временный пароль") : tr("Текущий пароль")}>
        <input className="input input--big" type="password" value={current} onChange={(e) => setCurrent(e.target.value)}
          autoComplete="current-password" required />
      </Field>
      <Field label={tr("Новый пароль")} hint={tr("Не короче 8 символов. Запишите его — восстановить можно только через администратора.")}>
        <input className="input input--big" type="password" value={next} onChange={(e) => setNext(e.target.value)}
          autoComplete="new-password" required />
      </Field>
      <Field label={tr("Повторите новый пароль")}>
        <input className="input input--big" type="password" value={repeat} onChange={(e) => setRepeat(e.target.value)}
          autoComplete="new-password" required />
      </Field>
      <SubmitButton pending={save.isPending}>{tr("Сохранить пароль")}</SubmitButton>
    </form>
  )
}

/** Full screen after logging in with a temporary password: nothing else works until it is changed. */
export function ForcedPasswordChange() {
  const { user, logout } = useAuth()
  return (
    <div className="state login">
      <span className="state__cell" aria-hidden><Icon name="shield" size={30} /></span>
      <h2 className="state__title">{tr("Придумайте свой пароль")}</h2>
      <p className="hint">{tr("Вы вошли с временным паролем от администратора. Замените его на свой — дальше входите с ним.")}</p>
      {user?.login && <p className="hint small">{tr("Ваш логин: {0}", user.login)}</p>}
      <ChangePasswordForm forced />
      <button type="button" className="btn btn--ghost btn--block" onClick={() => void logout()}>{tr("Выйти")}</button>
    </div>
  )
}

/** For the admin: login + temporary password, shown once, with a button to send it to the person. */
export function CredentialsCard({ creds, onDone }: { creds: AccountCredentials; onDone: () => void }) {
  const [note, setNote] = useState<string | null>(null)
  const message = tr("Вход в учёт пасеки Fayzi Umar: {0}\nЛогин: {1}\nВременный пароль: {2}\nПри первом входе придумайте свой пароль.",
    window.location.origin, creds.login, creds.temporary_password)
  const share = async () => {
    const how = await shareText(message)
    setNote(how === 'copied' ? tr("Текст скопирован — вставьте его в сообщение человеку.") : how === 'none' ? tr("Не удалось поделиться — перепишите логин и пароль вручную.") : null)
  }
  return (
    <div className="form">
      <div className="result-ok"><span className="result-ok__mark" aria-hidden>✓</span>
        <b>{creds.user.display_name}</b>
        <span className="hint small">{tr("Передайте человеку логин и временный пароль. Пароль показывается только сейчас.")}</span></div>
      <div className="creds">
        <div className="row"><span className="hint">{tr("Логин")}</span><b className="creds__value">{creds.login}</b></div>
        <div className="row"><span className="hint">{tr("Временный пароль")}</span><b className="creds__value">{creds.temporary_password}</b></div>
      </div>
      {note && <p className="hint small" role="status">{note}</p>}
      <button type="button" className="btn btn--primary btn--block" onClick={() => void share()}><Icon name="share" size={18} />{tr("Отправить человеку")}</button>
      <button type="button" className="btn btn--ghost btn--block" onClick={onDone}>{tr("Готово")}</button>
    </div>
  )
}
