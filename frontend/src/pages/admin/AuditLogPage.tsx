import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import { adminApi, usersApi } from '../../api/resources'
import { Icon } from '../../components/Icon'
import { LoadingView, MessageView } from '../../components/StateViews'
import { ErrorBox, Select } from '../../components/ui'
import { usePermissions } from '../../hooks/usePermissions'
import { ENTITY_LABEL, describeLogEntry, formatDateTime, logDetail } from '../../utils/labels'
import { tr } from '../../i18n'

const PAGE = 50

/** Every change in the system, newest first; filter by person and by section. */
export function AuditLogPage() {
  const { isAdmin, canAdminister } = usePermissions()
  const [userId, setUserId] = useState('')
  const [entity, setEntity] = useState('')
  const users = useQuery({ queryKey: ['users'], queryFn: usersApi.list, enabled: canAdminister })
  const log = useInfiniteQuery({
    queryKey: ['admin-audit', userId, entity],
    queryFn: ({ pageParam }) => adminApi.audit({ user_id: userId || undefined, entity_type: entity || undefined, offset: pageParam, limit: PAGE }),
    initialPageParam: 0,
    getNextPageParam: (last) => last.next_offset ?? undefined,
    enabled: canAdminister,
  })
  if (!canAdminister) return <MessageView icon="shield" title={isAdmin ? tr("Управление пользователями доступно только в панели владельца") : tr("Только для администратора")} />
  const items = log.data?.pages.flatMap((p) => p.items) ?? []
  const types = log.data?.pages[0]?.entity_types ?? []

  return (
    <div className="page">
      <h1 className="page__title">{tr("Журнал действий")}</h1>
      <div className="filter-row">
        <Select value={userId} onChange={setUserId} placeholder={tr("Все пользователи")}
          options={(users.data ?? []).map((u) => ({ value: u.id, label: u.display_name }))} />
        <Select value={entity} onChange={setEntity} placeholder={tr("Все разделы")}
          options={types.map((t) => ({ value: t, label: ENTITY_LABEL[t] ?? t }))} />
      </div>
      <ErrorBox error={log.error} />
      {log.isLoading ? <LoadingView /> : !items.length ? <MessageView icon="log" title={tr("Записей нет")} /> : (
        <section className="card">
          {items.map((e) => (
            <div key={e.id} className="log-row">
              <span className="log-row__icon" aria-hidden><Icon name={e.hive_id ? 'hive' : 'log'} size={16} /></span>
              <div>
                <div className="log-row__title">{describeLogEntry(e)}</div>
                {!e.hive_id && logDetail(e) && <div className="small">{logDetail(e)}</div>}
                {e.comment && <div className="small hint">«{e.comment}»</div>}
                <div className="log-row__meta">
                  {formatDateTime(e.created_at)} · {e.user_name ?? tr("система")} · {e.hive_id && e.hive_number
                    ? <Link className="link" to={`/hives/${e.hive_id}`}>{tr("улей №{0}", e.hive_number)}</Link>
                    : ENTITY_LABEL[e.entity_type] ?? e.entity_type}
                </div>
              </div>
            </div>
          ))}
        </section>
      )}
      {log.hasNextPage && (
        <button type="button" className="btn btn--secondary btn--block" disabled={log.isFetchingNextPage} onClick={() => log.fetchNextPage()}>
          {log.isFetchingNextPage ? tr("Загружаем…") : tr("Показать ещё")}
        </button>
      )}
    </div>
  )
}
