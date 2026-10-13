import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { adminApi } from '../../api/resources'
import { Icon } from '../../components/Icon'
import { LoadingView, MessageView } from '../../components/StateViews'
import { Badge, ErrorBox, InfoRow } from '../../components/ui'
import { usePermissions } from '../../hooks/usePermissions'
import { ROLE_LABELS, type UserRole } from '../../types/api'
import { formatDateTime } from '../../utils/labels'

const ENV: Record<string, string> = { production: 'боевой сервер', development: 'проверка на ноутбуке', test: 'тесты' }
const yesNo = (ok: boolean, yes: string, no: string) => <Badge tone={ok ? 'ok' : 'warn'}>{ok ? yes : no}</Badge>

/** «Админ-панель»: everything about the Mini App, plus entry points to access and the activity log. */
export function AdminPage() {
  const { isAdmin } = usePermissions()
  const overview = useQuery({ queryKey: ['admin-overview'], queryFn: adminApi.overview, enabled: isAdmin })
  if (!isAdmin) return <MessageView icon="shield" title="Только для администратора" />
  if (overview.isLoading) return <LoadingView />
  const o = overview.data
  const sections = o ? [...new Set(o.counts.map((c) => c.section))] : []

  return (
    <div className="page">
      <h1 className="page__title">Админ-панель</h1>
      <ErrorBox error={overview.error} />

      <nav className="menu">
        <Link to="/users" className="menu__item"><Icon name="users" />Пользователи и доступ
          {o && o.users.pending_invites > 0 && <span className="menu__hint">ждут входа: {o.users.pending_invites}</span>}
          <span className="chevron">›</span></Link>
        <Link to="/admin/log" className="menu__item"><Icon name="log" />Журнал действий<span className="chevron">›</span></Link>
      </nav>

      {o && <>
        <section className="card">
          <h2 className="card__title">Пользователи</h2>
          <div className="kv-grid">
            {(['ADMIN', 'BEEKEEPER', 'ASSISTANT', 'VIEWER'] as UserRole[]).map((r) => (
              <div key={r} className="kv"><span className="kv__value">{o.users[r] ?? 0}</span><span className="kv__label">{ROLE_LABELS[r]}</span></div>
            ))}
          </div>
          <InfoRow label="Заходили за 7 дней">{o.users.seen_7_days}</InfoRow>
          <InfoRow label="Заблокированы">{o.users.blocked}</InfoRow>
          <InfoRow label="Приглашены, ещё не входили">{o.users.pending_invites}</InfoRow>
        </section>

        {sections.map((sec) => (
          <section key={sec} className="card">
            <h2 className="card__title">{sec}</h2>
            {o.counts.filter((c) => c.section === sec).map((c) => <InfoRow key={c.label} label={c.label}>{c.value}</InfoRow>)}
          </section>
        ))}

        <section className="card">
          <h2 className="card__title">Система</h2>
          <InfoRow label="Режим">{ENV[o.system.environment] ?? o.system.environment}</InfoRow>
          <InfoRow label="Бот">{yesNo(o.system.bot_configured, o.system.bot_username ? `@${o.system.bot_username}` : 'подключён', 'токен не задан')}</InfoRow>
          <InfoRow label="QR-ссылки на бота">{yesNo(o.system.deep_links_ready, 'готовы', 'нет TELEGRAM_BOT_USERNAME')}</InfoRow>
          <InfoRow label="База данных">{yesNo(o.system.database_ok, o.system.database_size_mb !== null ? `${o.system.database_size_mb} МБ` : 'работает', 'нет связи')}</InfoRow>
          <InfoRow label="Версия схемы">{o.system.migration ?? '—'}</InfoRow>
          <InfoRow label="Часовой пояс">{o.system.timezone}</InfoRow>
          <InfoRow label="Валюта">{o.system.currency}</InfoRow>
          <InfoRow label="Время сервера">{formatDateTime(o.system.server_time)}</InfoRow>
        </section>
      </>}
    </div>
  )
}
