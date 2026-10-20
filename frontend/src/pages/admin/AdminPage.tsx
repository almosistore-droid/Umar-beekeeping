import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { adminApi } from '../../api/resources'
import { Icon } from '../../components/Icon'
import { LoadingView, MessageView } from '../../components/StateViews'
import { Badge, ErrorBox, InfoRow } from '../../components/ui'
import { usePermissions } from '../../hooks/usePermissions'
import { ROLE_LABELS, type UserRole } from '../../types/api'
import { formatDateTime } from '../../utils/labels'
import { tr } from '../../i18n'

const ENV: Record<string, string> = { production: tr("боевой сервер"), development: tr("проверка на ноутбуке"), test: tr("тесты") }
const yesNo = (ok: boolean, yes: string, no: string) => <Badge tone={ok ? 'ok' : 'warn'}>{ok ? yes : no}</Badge>

/** «Админ-панель»: everything about the Mini App, plus entry points to access and the activity log. */
export function AdminPage() {
  const { isAdmin, canAdminister } = usePermissions()
  const overview = useQuery({ queryKey: ['admin-overview'], queryFn: adminApi.overview, enabled: canAdminister })
  if (!canAdminister) return <MessageView icon="shield" title={isAdmin ? tr("Управление пользователями доступно только в панели владельца") : tr("Только для администратора")} />
  if (overview.isLoading) return <LoadingView />
  const o = overview.data
  const sections = o ? [...new Set(o.counts.map((c) => c.section))] : []

  return (
    <div className="page">
      <h1 className="page__title">{tr("Админ-панель")}</h1>
      <ErrorBox error={overview.error} />

      <nav className="menu">
        <Link to="/users" className="menu__item"><Icon name="users" />{tr("Пользователи и доступ")}{o && o.users.pending_invites > 0 && <span className="menu__hint">{tr("ждут входа: {0}", o.users.pending_invites)}</span>}
          <span className="chevron">›</span></Link>
        <Link to="/admin/log" className="menu__item"><Icon name="log" />{tr("Журнал действий")}<span className="chevron">›</span></Link>
      </nav>

      {o && <>
        <section className="card">
          <h2 className="card__title">{tr("Пользователи")}</h2>
          <div className="kv-grid">
            {(['ADMIN', 'BEEKEEPER', 'ASSISTANT', 'VIEWER'] as UserRole[]).map((r) => (
              <div key={r} className="kv"><span className="kv__value">{o.users[r] ?? 0}</span><span className="kv__label">{ROLE_LABELS[r]}</span></div>
            ))}
          </div>
          <InfoRow label={tr("Заходили за 7 дней")}>{o.users.seen_7_days}</InfoRow>
          <InfoRow label={tr("Заблокированы")}>{o.users.blocked}</InfoRow>
          <InfoRow label={tr("Приглашены, ещё не входили")}>{o.users.pending_invites}</InfoRow>
        </section>

        {sections.map((sec) => (
          <section key={sec} className="card">
            <h2 className="card__title">{sec}</h2>
            {o.counts.filter((c) => c.section === sec).map((c) => <InfoRow key={c.label} label={c.label}>{c.value}</InfoRow>)}
          </section>
        ))}

        <section className="card">
          <h2 className="card__title">{tr("Система")}</h2>
          <InfoRow label={tr("Режим")}>{ENV[o.system.environment] ?? o.system.environment}</InfoRow>
          <InfoRow label={tr("Бот")}>{yesNo(o.system.bot_configured, o.system.bot_username ? `@${o.system.bot_username}` : tr("подключён"), tr("токен не задан"))}</InfoRow>
          <InfoRow label={tr("QR-ссылки на бота")}>{yesNo(o.system.deep_links_ready, tr("готовы"), tr("нет TELEGRAM_BOT_USERNAME"))}</InfoRow>
          <InfoRow label={tr("База данных")}>{yesNo(o.system.database_ok, o.system.database_size_mb !== null ? tr("{0} МБ", o.system.database_size_mb) : tr("работает"), tr("нет связи"))}</InfoRow>
          <InfoRow label={tr("Версия схемы")}>{o.system.migration ?? '—'}</InfoRow>
          <InfoRow label={tr("Часовой пояс")}>{o.system.timezone}</InfoRow>
          <InfoRow label={tr("Валюта")}>{o.system.currency}</InfoRow>
          <InfoRow label={tr("Время сервера")}>{formatDateTime(o.system.server_time)}</InfoRow>
        </section>
      </>}
    </div>
  )
}
