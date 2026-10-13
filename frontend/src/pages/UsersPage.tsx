import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { usersApi } from '../api/resources'
import { ErrorBox, Select } from '../components/ui'
import { LoadingView, MessageView } from '../components/StateViews'
import { useAuth } from '../hooks/useAuth'
import { usePermissions } from '../hooks/usePermissions'
import { haptic } from '../services/telegram'
import { ROLE_LABELS, type UserRole } from '../types/api'

const roleOpts = (Object.keys(ROLE_LABELS) as UserRole[]).map((r) => ({ value: r, label: ROLE_LABELS[r] }))

export function UsersPage() {
  const { isAdmin } = usePermissions()
  const me = useAuth().user
  const qc = useQueryClient()
  const users = useQuery({ queryKey: ['users'], queryFn: usersApi.list, enabled: isAdmin })
  const update = useMutation({
    mutationFn: ({ id, ...body }: { id: string; role?: UserRole; is_active?: boolean }) => usersApi.update(id, body),
    onSuccess: () => { haptic('success'); qc.invalidateQueries({ queryKey: ['users'] }) },
    onError: () => haptic('error'),
  })

  if (!isAdmin) return <MessageView icon="users" title="Только для администратора" />
  if (users.isLoading) return <LoadingView />

  return (
    <div className="page">
      <h1 className="page__title">Пользователи</h1>
      <p className="hint">Новые пользователи появляются здесь после первого входа в приложение через Telegram.</p>
      <ErrorBox error={users.error ?? update.error} />
      <ul className="list">
        {users.data?.map((u) => (
          <li key={u.id} className={`card${u.is_active ? '' : ' card--muted'}`}>
            <div className="card__titlebar">
              <h2 className="card__title">{u.display_name}{u.id === me?.id && ' (вы)'}</h2>
              {u.username && <span className="hint small">@{u.username}</span>}
            </div>
            {u.id !== me?.id && <>
              <Select value={u.role} onChange={(role) => update.mutate({ id: u.id, role })} options={roleOpts} />
              <label className="switch">
                <input type="checkbox" checked={u.is_active} onChange={(e) => update.mutate({ id: u.id, is_active: e.target.checked })} />
                <span>Доступ разрешён</span>
              </label>
            </>}
            {u.id === me?.id && <p className="hint small">{ROLE_LABELS[u.role]}</p>}
          </li>
        ))}
      </ul>
      <section className="card card--muted small">
        <b>Роли</b>
        <span><b>Администратор:</b> всё, включая пользователей</span>
        <span><b>Пчеловод:</b> пасеки, ульи, семьи, матки</span>
        <span><b>Помощник:</b> записи (сила семьи, позже осмотры)</span>
        <span><b>Наблюдатель:</b> только просмотр</span>
      </section>
    </div>
  )
}
