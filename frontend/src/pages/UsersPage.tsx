import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { adminApi, usersApi } from '../api/resources'
import { Icon } from '../components/Icon'
import { Choice, ErrorBox, Field, Select, Sheet, SubmitButton, fieldError } from '../components/ui'
import { LoadingView, MessageView } from '../components/StateViews'
import { useAuth } from '../hooks/useAuth'
import { usePermissions } from '../hooks/usePermissions'
import { haptic, shareText } from '../services/telegram'
import { ROLE_LABELS, type InviteResult, type UserRole } from '../types/api'
import { agoLabel, formatDate } from '../utils/labels'

const roleOpts = (Object.keys(ROLE_LABELS) as UserRole[]).map((r) => ({ value: r, label: ROLE_LABELS[r] }))
const ROLE_HINT: Record<UserRole, string> = {
  ADMIN: 'всё, включая пользователей и админ-панель',
  BEEKEEPER: 'пасеки, ульи, матки, операции, CRM',
  ASSISTANT: 'осмотры, болезни, обработки, подкормки, мёд',
  VIEWER: 'только просмотр, без денег',
}

/** Admin: users and access — roles, blocking, adding people in advance (invitations). */
export function UsersPage() {
  const { isAdmin } = usePermissions()
  const me = useAuth().user
  const qc = useQueryClient()
  const [adding, setAdding] = useState(false)
  const users = useQuery({ queryKey: ['users'], queryFn: usersApi.list, enabled: isAdmin })
  const invites = useQuery({ queryKey: ['invites'], queryFn: adminApi.invites, enabled: isAdmin })
  const refresh = () => ['users', 'invites', 'admin-overview'].forEach((k) => qc.invalidateQueries({ queryKey: [k] }))
  const update = useMutation({
    mutationFn: ({ id, ...body }: { id: string; role?: UserRole; is_active?: boolean }) => usersApi.update(id, body),
    onSuccess: () => { haptic('success'); refresh() },
    onError: () => haptic('error'),
  })
  const revoke = useMutation({ mutationFn: adminApi.revoke, onSuccess: () => { haptic('success'); refresh() }, onError: () => haptic('error') })

  if (!isAdmin) return <MessageView icon="users" title="Только для администратора" />
  if (users.isLoading) return <LoadingView />
  const pending = (invites.data ?? []).filter((i) => i.status === 'PENDING' && !i.expired)

  return (
    <div className="page">
      <div className="page__titlebar">
        <h1 className="page__title">Пользователи и доступ</h1>
        <button className="btn btn--primary btn--sm" onClick={() => setAdding(true)}>＋ Добавить</button>
      </div>
      <ErrorBox error={users.error ?? update.error ?? revoke.error} />

      {pending.length > 0 && (
        <section className="card">
          <h2 className="card__title">Ждут первого входа</h2>
          {pending.map((i) => (
            <div key={i.id} className="invite-row">
              <span className="invite-row__who">
                <b>{i.note ?? (i.username ? `@${i.username}` : `ID ${i.telegram_id}`)}</b>
                <span className="hint small">
                  {[i.username && `@${i.username}`, i.telegram_id && `ID ${i.telegram_id}`].filter(Boolean).join(' · ')} · {ROLE_LABELS[i.role]} · до {formatDate(i.expires_at)}
                </span>
              </span>
              <button type="button" className="btn btn--ghost btn--sm" disabled={revoke.isPending}
                onClick={() => revoke.mutate(i.id)}>Отозвать</button>
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
                <h2 className="card__title">{u.display_name}{self && ' (вы)'}</h2>
                {!u.is_active && <span className="badge badge--bad">заблокирован</span>}
              </div>
              <div className="user-row__meta">
                {u.username && <span>@{u.username}</span>}
                <span>ID {u.telegram_id}</span>
                <span>был(а): {agoLabel(u.last_seen_at)}</span>
              </div>
              {self ? <p className="hint small">{ROLE_LABELS[u.role]}</p> : <>
                <Select value={u.role} onChange={(role) => update.mutate({ id: u.id, role })} options={roleOpts} />
                <label className="switch">
                  <input type="checkbox" checked={u.is_active} onChange={(e) => update.mutate({ id: u.id, is_active: e.target.checked })} />
                  <span>Доступ разрешён</span>
                </label>
              </>}
            </li>
          )
        })}
      </ul>

      <section className="card card--muted small">
        <b>Роли</b>
        {(Object.keys(ROLE_HINT) as UserRole[]).map((r) => <span key={r}><b>{ROLE_LABELS[r]}:</b> {ROLE_HINT[r]}</span>)}
      </section>

      <Sheet open={adding} title="Добавить пользователя" onClose={() => setAdding(false)}>
        {adding && <InviteForm onDone={() => { refresh(); setAdding(false) }} />}
      </Sheet>
    </div>
  )
}

function InviteForm({ onDone }: { onDone: () => void }) {
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
    onSuccess: (r) => { haptic('success'); setResult(r) },
    onError: () => haptic('error'),
  })

  if (result) {
    if (result.kind === 'updated') {
      return (
        <div className="form">
          <div className="result-ok"><span className="result-ok__mark" aria-hidden>✓</span>
            <b>{result.user?.display_name} уже пользуется приложением</b>
            <span className="hint small">Роль изменена на «{ROLE_LABELS[result.user!.role]}», доступ открыт.</span></div>
          <button type="button" className="btn btn--primary btn--block" onClick={onDone}>Готово</button>
        </div>
      )
    }
    const share = async () => {
      const how = await shareText(result.share_text ?? '')
      setShared(how === 'copied' ? 'Текст скопирован — вставьте его в чат с человеком.' : how === 'none' ? 'Не удалось поделиться — скопируйте текст вручную.' : null)
    }
    return (
      <div className="form">
        <div className="result-ok"><span className="result-ok__mark" aria-hidden>✓</span><b>Приглашение создано</b>
          <span className="hint small">При первом входе человек сразу получит роль «{ROLE_LABELS[result.invite!.role]}». Приглашение действует 30 дней.</span></div>
        <p className="hint small">Отправьте человеку сообщение:</p>
        <p className="share-box">{result.share_text}</p>
        {shared && <p className="hint small" role="status">{shared}</p>}
        <button type="button" className="btn btn--primary btn--block" onClick={share}><Icon name="share" size={18} />Отправить приглашение</button>
        <button type="button" className="btn btn--ghost btn--block" onClick={onDone}>Готово</button>
      </div>
    )
  }

  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate() }}>
      <ErrorBox error={save.error} />
      <Choice label="Как найти человека" value={by} onChange={(v) => { if (v) { setBy(v); setValue('') } }}
        options={[{ value: 'username', label: 'По @username' }, { value: 'id', label: 'По Telegram ID' }]} />
      {by === 'username' ? (
        <Field label="Имя пользователя в Telegram" hint="Есть в профиле Telegram: «@имя»" error={fieldError(save.error, 'username')}>
          <input className="input input--big" value={value} onChange={(e) => setValue(e.target.value)} placeholder="@username"
            autoCapitalize="off" autoComplete="off" spellCheck={false} required />
        </Field>
      ) : (
        <Field label="Telegram ID" hint="Число. Человек может узнать его у бота @userinfobot" error={fieldError(save.error, 'telegram_id')}>
          <input className="input input--big" inputMode="numeric" value={value} onChange={(e) => setValue(e.target.value.replace(/\D/g, ''))} required />
        </Field>
      )}
      <Choice label="Роль" options={roleOpts} value={role} onChange={(v) => v && setRole(v)} />
      <p className="hint small">{ROLE_HINT[role]}</p>
      <Field label="Кто это" hint="Например «Карим, помощник на горной пасеке»">
        <input className="input" value={note} onChange={(e) => setNote(e.target.value)} maxLength={200} />
      </Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending}>Добавить</SubmitButton></div>
    </form>
  )
}
