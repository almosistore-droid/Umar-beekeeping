import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiariesApi, hivesApi } from '../api/resources'
import { Icon } from '../components/Icon'
import { Badge, Chips, ErrorBox, Fab, StrengthBars } from '../components/ui'
import { LoadingView, MessageView } from '../components/StateViews'
import { usePermissions } from '../hooks/usePermissions'
import type { FamilyStrength, HiveStatus } from '../types/api'
import { HIVE_STATUS, STRENGTH } from '../utils/labels'

type Filter = 'all' | 'inspection' | 'strong' | 'weak' | 'queenless' | 'sick' | 'empty' | 'archive'
const FILTERS: { value: Filter; label: string; statuses?: HiveStatus[]; strengths?: FamilyStrength[]; needsInspection?: boolean }[] = [
  { value: 'all', label: 'Все' },
  { value: 'inspection', label: 'Требуют осмотра', needsInspection: true },
  { value: 'strong', label: 'Сильные', strengths: ['STRONG', 'VERY_STRONG'] },
  { value: 'weak', label: 'Слабые', strengths: ['WEAK', 'VERY_WEAK'] },
  { value: 'queenless', label: 'Без матки', statuses: ['QUEENLESS'] },
  { value: 'sick', label: 'Больные', statuses: ['SICK', 'QUARANTINE'] },
  { value: 'empty', label: 'Пустые', statuses: ['EMPTY'] },
  { value: 'archive', label: 'Архив', statuses: ['SOLD', 'LOST', 'MERGED'] },
]

export function HivesPage() {
  const { canManage } = usePermissions()
  const [params] = useSearchParams()
  const [apiaryId, setApiaryId] = useState<string>(params.get('apiary') ?? 'all')
  const [filter, setFilter] = useState<Filter>((params.get('filter') as Filter) ?? 'all')
  const [q, setQ] = useState('')

  const apiaries = useQuery({ queryKey: ['apiaries'], queryFn: () => apiariesApi.list() })
  const current = FILTERS.find((f) => f.value === filter)
  const hives = useQuery({
    queryKey: ['hives', apiaryId, filter, q],
    queryFn: () => hivesApi.list({
      apiary_id: apiaryId === 'all' ? undefined : apiaryId, status: current?.statuses, strength: current?.strengths, needs_inspection: current?.needsInspection, q: q || undefined,
    }),
  })

  const apiaryOptions = useMemo(
    () => [{ value: 'all', label: 'Все пасеки' }, ...(apiaries.data ?? []).map((a) => ({ value: a.id, label: a.name }))],
    [apiaries.data],
  )

  if (apiaries.data && apiaries.data.length === 0) {
    return (
      <div className="page">
        <h1 className="page__title">Ульи</h1>
        <MessageView icon="apiary" title="Сначала создайте пасеку"
          text={canManage ? 'Ульи привязываются к пасеке.' : 'Попросите пчеловода добавить пасеку.'} />
        {canManage && <Link className="btn btn--primary btn--block" to="/apiaries">Создать пасеку</Link>}
      </div>
    )
  }

  return (
    <div className="page">
      <div className="page__titlebar">
        <h1 className="page__title">Ульи</h1>
        {hives.data && <span className="hint">{hives.data.total}</span>}
      </div>
      <input className="input input--search" type="search" placeholder="Номер улья или код матки"
        value={q} onChange={(e) => setQ(e.target.value)} />
      {apiaryOptions.length > 2 && <Chips options={apiaryOptions} value={apiaryId} onChange={setApiaryId} />}
      <Chips options={FILTERS} value={filter} onChange={setFilter} />

      <ErrorBox error={hives.error} />
      {hives.isLoading ? <LoadingView /> : hives.data?.items.length === 0 ? (
        <MessageView icon="hive" title="Ульев не найдено" text={q || filter !== 'all' ? 'Измените фильтр или поиск.' : undefined} />
      ) : (
        <ul className="list">
          {hives.data?.items.map((h) => {
            const st = HIVE_STATUS[h.status]
            return (
              <li key={h.id}>
                <Link to={`/hives/${h.id}`} className="hive-card">
                  <div className={`hive-card__num${h.hive_number.length > 3 ? ' hive-card__num--long' : ''}`} aria-label={`Улей №${h.hive_number}`}>{h.hive_number}</div>
                  <div className="hive-card__body">
                    <div className="hive-card__top">
                      <Badge tone={st.tone}>{st.label}</Badge>

                    </div>
                    <div className="hive-card__meta">
                      {h.strength ? <StrengthBars bars={STRENGTH[h.strength].bars} label={STRENGTH[h.strength].label} /> : <span className="hint">Нет семьи</span>}
                    </div>
                    {apiaryId === 'all' && apiaryOptions.length > 2 && <div className="hive-card__apiary">{h.apiary.name}</div>}
                    <div className="hive-card__meta hint small">
                      {h.queen_code ? <><Icon name="crown" size={14} className="inline-icon" />{h.queen_code}{h.queen_age_label && `, ${h.queen_age_label}`}</> : h.strength ? 'Матка не записана' : ''}
                    </div>
                  </div>
                  <span className="chevron" aria-hidden>›</span>
                </Link>
              </li>
            )
          })}
        </ul>
      )}
      {canManage && <Fab to="/hives/new" label="Улей" />}
    </div>
  )
}
