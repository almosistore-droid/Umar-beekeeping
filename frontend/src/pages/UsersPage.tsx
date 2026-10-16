import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { adminApi, usersApi } from '../api/resources'
import { Icon } from '../components/Icon'
import { Choice, ErrorBox, Field, Select, Sheet, SubmitButton, fieldError } from '../components/ui'
import { LoadingView, MessageView } from '../components/StateViews'
import { useAuth } from '../hooks/useAuth'
import { usePermissions } from '../hooks/usePermissions'
import { haptic, shareText } from '../services/telegram'
import { ROLE_LABELS, type AccountCredentials, type InviteResult, type User, type UserRole } from '../types/api'
import { CredentialsCard } from '../components/auth/PasswordForms'
import { agoLabel, formatDate } from '../utils/labels'
import { tr } from '../i18n'

const roleOpts = (Object.keys(ROLE_LABELS) as UserRole[]).map((r) => ({ value: r, label: ROLE_LABELS[r] }))
const ROLE_HINT: Record<UserRole, string> = {
  ADMIN: tr("всё, включая пользователей и админ-панель"),
  BEEKEEPER: tr("пасеки, ульи, матки, операции, CRM"),
  ASSISTANT: tr("осмотры, болезни, обработки, подкормки, мёд"),
  VIEWER: tr("только просмотр, без денег"),
}

/** Admin: users and access — roles, blocking, adding people in advance (invitations). */
export function UsersPage() {
  const { isAdmin } = usePermissions()
  const me = useAuth().user
  const qc = useQueryClient()
  const [adding, setAdding] = useState(false)
  const [passwordFor, setPasswordFor] = useState<User | null>(null)
  const users = useQuery({ queryKey: ['users'], queryFn: usersApi.list, enabled: isAdmin })
  const invites = useQuery({ queryKey: ['invites'], queryFn: adminApi.invites, enabled: isAdmin })
  const refresh = () => ['users', 'invites', 'admin-overview'].forEach((k) => qc.invalidateQueries({ queryKey: [k] }))
  const update = useMutation({
    mutationFn: ({ id, ...body }: { id: string; role?: UserRole; is_active?: boolean }) => usersApi.update(id, body),
    onSuccess: () => { haptic('success'); refresh() },
    onError: () => haptic('error'),
  })
  const revoke = useMutation({ mutationFn: adminApi.revoke, onSuccess: () => { haptic('success'); refresh() }, onError: () => haptic('error') })

  if (!isAdmin) return <MessageView icon="users" title={tr("Только для администратора")} />
  if (users.isLoading) return <LoadingView />
  const pending = (invites.data ?? []).filter((i) => i.status === 'PENDING' && !i.expired)

  return (
    <div className="page">
      <div className="page__titlebar">
        <h1 className="page__title">{tr("Пользователи и доступ")}</h1>
        <button className="btn btn--primary btn--sm" onClick={() => setAdding(true)}>{tr("＋ Добавить")}</button>
      </div>
      <ErrorBox error={users.error ?? update.error ?? revoke.error} />

      {pending.length > 0 && (
        <section className="card">
          <h2 className="card__title">{tr("Ждут первого входа")}</h2>
          {pending.map((i) => (
            <div key={i.id} className="invite-row">
              <span className="invite-row__who">
                <b>{i.note ?? (i.username ? `@${i.username}` : `ID ${i.telegram_id}`)}</b>
                <span className="hint small">{tr("{0} · {1} · до {2}", [i.username && `@${i.username}`, i.telegram_id && `ID ${i.telegram_id}`].filter(Boolean).join(' · '), ROLE_LABELS[i.role], formatDate(i.expires_at))}</span>
              </span>
              <button type="button" className="btn btn--ghost btn--sm" disabled={revoke.isPending}
                onClick={() => revoke.mutate(i.id)}>{tr("Отозвать")}</button>
            </div>
          ))}
        </section>
      )}

      <ul className="list">
        {users.data?.map((u) => {
          const self = u.id === me?.id
          return (
            <li key={u.id} className={`card user-row${u.is_active ? '' : ' card--muted'}`}>
              <div className="card__titlebar">
                <h2 className="card__title">{u.display_name}{self && tr(" (вы)")}</h2>
                {!u.is_active && <span className="badge badge--bad">{tr("заблокирован")}</span>}
              </div>
              <div className="user-row__meta">
                {u.username && <span>@{u.username}</span>}
                {u.telegram_id && <span>ID {u.telegram_id}</span>}
                {u.login && <span>{tr("логин: {0}", u.login)}</span>}
                <span>{tr("был(а): {0}", agoLabel(u.last_seen_at))}</span>
              </div>
              {self ? <p className="hint small">{ROLE_LABELS[u.role]}</p> : <>
                <Select value={u.role} onChange={(role) => update.mutate({ id: u.id, role })} options={roleOpts} />
                <label className="switch">
                  <input type="checkbox" checked={u.is_active} onChange={(e) => update.mutate({ id: u.id, is_active: e.target.checked })} />
                  <span>{tr("Доступ разрешён")}</span>
                </label>
                <button type="button" className="btn btn--ghost btn--sm" onClick={() => setPasswordFor(u)}>
                  <Icon name="shield" size={16} />{u.login ? tr("Новый пароль") : tr("Вход по паролю")}
                </button>
              </>}
            </li>
          )
        })}
      </ul>

      <section className="card card--muted small">
        <b>{tr("Роли")}</b>
        {(Object.keys(ROLE_HINT) as UserRole[]).map((r) => <span key={r}><b>{ROLE_LABELS[r]}:</b> {ROLE_HINT[r]}</span>)}
      </section>

      <Sheet open={adding} title={tr("Добавить пользователя")} onClose={() => setAdding(false)}>
        {adding && <AddUser onDone={() => { refresh(); setAdding(false) }} />}
      </Sheet>
      <Sheet open={!!passwordFor} title={passwordFor?.login ? tr("Новый пароль") : tr("Вход по паролю")} onClose={() => setPasswordFor(null)}>
        {passwordFor && <ResetPasswordForm user={passwordFor} onDone={() => { refresh(); setPasswordFor(null) }} />}
      </Sheet>
    </div>
  )
}

/** Two ways to add a person: through Telegram (invitation) or a login and password (no Telegram needed). */
function AddUser({ onDone }: { onDone: () => void }) {
  const [how, setHow] = useState<'telegram' | 'password'>('telegram')
  const [creds, setCreds] = useState<AccountCredentials | null>(null)
  const [invited, setInvited] = useState(false)
  if (creds) return <CredentialsCard creds={creds} onDone={onDone} />
  return (
    <>
      {!invited && (
        <Choice label={tr("Как человек будет входить")} value={how} onChange={(v) => v && setHow(v)}
          options={[{ value: 'telegram', label: tr("Через Telegram") }, { value: 'password', label: tr("Логин и пароль") }]} />
      )}
      {how === 'telegram' ? <InviteForm onDone={onDone} onResult={() => setInvited(true)} /> : <AccountForm onCreated={setCreds} />}
    </>
  )
}

function AccountForm({ onCreated }: { onCreated: (c: AccountCredentials) => void }) {
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [login, setLogin] = useState('')
  const [role, setRole] = useState<UserRole>('ASSISTANT')
  const save = useMutation({
    mutationFn: () => adminApi.createAccount({ first_name: firstName.trim(), last_name: lastName.trim() || null, login: login.trim(), role }),
    onSuccess: (c) => { haptic('success'); onCreated(c) },
    onError: () => haptic('error'),
  })
  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate() }}>
      <ErrorBox error={save.error} />
      <p className="hint small">{tr("Для тех, у кого нет Telegram. Вы получите временный пароль — человек сменит его при первом входе.")}</p>
      <Field label={tr("Имя")}>
        <input className="input input--big" value={firstName} onChange={(e) => setFirstName(e.target.value)} maxLength={128} required />
      </Field>
      <Field label={tr("Фамилия")}>
        <input className="input" value={lastName} onChange={(e) => setLastName(e.target.value)} maxLength={128} />
      </Field>
      <Field label={tr("Логин")} hint={tr("Латинские буквы и цифры, например karim или karim.bee")}>
        <input className="input input--big" value={login} onChange={(e) => setLogin(e.target.value.toLowerCase())}
          autoCapitalize="off" autoComplete="off" spellCheck={false} maxLength={32} required />
      </Field>
      <Choice label={tr("Роль")} options={roleOpts} value={role} onChange={(v) => v && setRole(v)} />
      <p className="hint small">{ROLE_HINT[role]}</p>
      <div className="submit-bar"><SubmitButton pending={save.isPending}>{tr("Создать вход")}</SubmitButton></div>
    </form>
  )
}

/** New temporary password, or a first login for someone who used only Telegram. */
function ResetPasswordForm({ user, onDone }: { user: User; onDone: () => void }) {
  const [login, setLogin] = useState(user.login ?? '')
  const [creds, setCreds] = useState<AccountCredentials | null>(null)
  const save = useMutation({
    mutationFn: () => adminApi.resetPassword(user.id, user.login ? null : login.trim()),
    onSuccess: (c) => { haptic('success'); setCreds(c) },
    onError: () => haptic('error'),
  })
  if (creds) return <CredentialsCard creds={creds} onDone={onDone} />
  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate() }}>
      <ErrorBox error={save.error} />
      <p><b>{user.display_name}</b></p>
      {user.login ? (
        <p className="hint small">{tr("Старый пароль перестанет работать, и человек выйдет из приложения на всех телефонах. Новый временный пароль он сменит при входе.")}</p>
      ) : (
        <>
          <p className="hint small">{tr("Человек сможет входить и без Telegram — по логину и паролю. Аккаунт и данные те же.")}</p>
          <Field label={tr("Логин")} hint={tr("Латинские буквы и цифры, например karim или karim.bee")}>
            <input className="input input--big" value={login} onChange={(e) => setLogin(e.target.value.toLowerCase())}
              autoCapitalize="off" autoComplete="off" spellCheck={false} maxLength={32} required />
          </Field>
        </>
      )}
      <SubmitButton pending={save.isPending}>{tr("Создать временный пароль")}</SubmitButton>
    </form>
  )
}

function InviteForm({ onDone, onResult }: { onDone: () => void; onResult?: () => void }) {
  const [by, setBy] = useState<'username' | 'id'>('username')
  const [value, setValue] = useState('')
  const [role, setRole] = useState<UserRole>('ASSISTANT')
  const [note, setNote] = useState('')
  const [result, setResult] = useState<InviteResult | null>(null)
  const [shared, setShared] = useState<string | null>(null)
  const save = useMutation({
    mutationFn: () => adminApi.invite({
      ...(by === 'id' ? { telegram_id: Number(value.trim()) } : { username: value }),
      role, note: note || null,
    }),
    onSuccess: (r) => { haptic('success'); setResult(r); onResult?.() },
    onError: () => haptic('error'),
  })

  if (result) {
    if (result.kind === 'updated') {
      return (
        <div className="form">
          <div className="result-ok"><span className="result-ok__mark" aria-hidden>✓</span>
            <b>{tr("{0} уже пользуется приложением", result.user?.display_name)}</b>
            <span className="hint small">{tr("Роль изменена на «{0}», доступ открыт.", ROLE_LABELS[result.user!.role])}</span></div>
          <button type="button" className="btn btn--primary btn--block" onClick={onDone}>{tr("Готово")}</button>
        </div>
      )
    }
    const share = async () => {
      const how = await shareText(result.share_text ?? '')
      setShared(how === 'copied' ? tr("Текст скопирован — вставьте его в чат с человеком.") : how === 'none' ? tr("Не удалось поделиться — скопируйте текст вручную.") : null)
    }
    return (
      <div className="form">
        <div className="result-ok"><span className="result-ok__mark" aria-hidden>✓</span><b>{tr("Приглашение создано")}</b>
          <span className="hint small">{tr("При первом входе человек сразу получит роль «{0}». Приглашение действует 30 дней.", ROLE_LABELS[result.invite!.role])}</span></div>
        <p className="hint small">{tr("Отправьте человеку сообщение:")}</p>
        <p className="share-box">{result.share_text}</p>
        {shared && <p className="hint small" role="status">{shared}</p>}
        <button type="button" className="btn btn--primary btn--block" onClick={share}><Icon name="share" size={18} />{tr("Отправить приглашение")}</button>
        <button type="button" className="btn btn--ghost btn--block" onClick={onDone}>{tr("Готово")}</button>
      </div>
    )
  }

  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate() }}>
      <ErrorBox error={save.error} />
      <Choice label={tr("Как найти человека")} value={by} onChange={(v) => { if (v) { setBy(v); setValue('') } }}
        options={[{ value: 'username', label: tr("По @username") }, { value: 'id', label: tr("По Telegram ID") }]} />
      {by === 'username' ? (
        <Field label={tr("Имя пользователя в Telegram")} hint={tr("Есть в профиле Telegram: «@имя»")} error={fieldError(save.error, 'username')}>
          <input className="input input--big" value={value} onChange={(e) => setValue(e.target.value)} placeholder="@username"
            autoCapitalize="off" autoComplete="off" spellCheck={false} required />
        </Field>
      ) : (
        <Field label="Telegram ID" hint={tr("Число. Человек может узнать его у бота @userinfobot")} error={fieldError(save.error, 'telegram_id')}>
          <input className="input input--big" inputMode="numeric" value={value} onChange={(e) => setValue(e.target.value.replace(/\D/g, ''))} required />
        </Field>
      )}
      <Choice label={tr("Роль")} options={roleOpts} value={role} onChange={(v) => v && setRole(v)} />
      <p className="hint small">{ROLE_HINT[role]}</p>
      <Field label={tr("Кто это")} hint={tr("Например «Карим, помощник на горной пасеке»")}>
        <input className="input" value={note} onChange={(e) => setNote(e.target.value)} maxLength={200} />
      </Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending}>{tr("Добавить")}</SubmitButton></div>
    </form>
  )
}
