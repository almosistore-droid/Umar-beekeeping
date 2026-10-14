import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { hivesApi } from '../api/resources'
import { ApiError } from '../api/client'
import { Icon } from '../components/Icon'
import { LoadingView, MessageView } from '../components/StateViews'
import { Badge, ErrorBox } from '../components/ui'
import { HiveMiniHead } from '../components/visit/HiveMiniHead'
import { usePermissions } from '../hooks/usePermissions'
import { HIVE_STATUS } from '../utils/labels'
import { tr } from '../i18n'

/** After a QR scan: «Осмотр» (full inspection, saved as a dated record) or «Проверка» (state summary). */
export function HiveVisitPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { canWrite } = usePermissions()
  const hive = useQuery({ queryKey: ['hive', id], queryFn: () => hivesApi.get(id) })

  if (hive.isLoading) return <LoadingView />
  if (hive.error) {
    return hive.error instanceof ApiError && hive.error.status === 404
      ? <MessageView icon="hive" title={tr("Улей не найден")} />
      : <div className="page"><ErrorBox error={hive.error} /></div>
  }
  const h = hive.data!
  const st = HIVE_STATUS[h.status]
  const canInspect = canWrite && !h.is_archived && !!h.current_family
  const inspectHint = !canWrite ? tr("Только просмотр") : h.is_archived ? tr("Улей в архиве") : !h.current_family ? tr("В улье нет семьи") : tr("Всё кнопками, сохранится с датой")

  return (
    <div className="page">
      <HiveMiniHead number={h.hive_number} apiary={h.apiary.name} />
      <div className="row row--start"><Badge tone={st.tone}>{st.label}</Badge></div>
      <p className="hint">{tr("Что делаем с ульем?")}</p>
      <div className="visit-choice">
        <button type="button" className="visit-choice__btn visit-choice__btn--primary" disabled={!canInspect}
          onClick={() => navigate(`/hives/${h.id}/inspect`)}>
          <span className="visit-choice__icon"><Icon name="inspect" size={30} /></span>
          <span className="visit-choice__title">{tr("Осмотр")}</span>
          <span className="visit-choice__hint">{inspectHint}</span>
        </button>
        <button type="button" className="visit-choice__btn" onClick={() => navigate(`/hives/${h.id}/check`)}>
          <span className="visit-choice__icon"><Icon name="health" size={30} /></span>
          <span className="visit-choice__title">{tr("Проверка")}</span>
          <span className="visit-choice__hint">{tr("Итог: как сейчас улей")}</span>
        </button>
      </div>
      <Link className="btn btn--ghost btn--block" to={`/hives/${h.id}`}>{tr("Паспорт улья")}</Link>
    </div>
  )
}
