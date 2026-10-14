import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { hivesApi } from '../api/resources'
import { InspectionForm } from '../components/health/InspectionForm'
import { Icon } from '../components/Icon'
import { LoadingView, MessageView } from '../components/StateViews'
import { ErrorBox } from '../components/ui'
import { HiveMiniHead } from '../components/visit/HiveMiniHead'
import { usePermissions } from '../hooks/usePermissions'
import { tr } from '../i18n'

/** Full-screen inspection for use at the hive; after saving — next hive or the hive passport. */
export function HiveInspectPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { canWrite } = usePermissions()
  const hive = useQuery({ queryKey: ['hive', id], queryFn: () => hivesApi.get(id) })

  if (hive.isLoading) return <LoadingView />
  if (hive.error) return <div className="page"><ErrorBox error={hive.error} /></div>
  const h = hive.data!
  if (!canWrite || h.is_archived || !h.current_family) {
    return <MessageView icon="inspect" title={tr("Осмотр недоступен")}
      text={!canWrite ? tr("Ваша роль — только просмотр.") : h.is_archived ? tr("Улей в архиве.") : tr("В улье нет пчелиной семьи.")}
      action={{ label: tr("Паспорт улья"), onClick: () => navigate(`/hives/${h.id}`, { replace: true }) }} />
  }

  return (
    <div className="page">
      <HiveMiniHead number={h.hive_number} apiary={h.apiary.name} />
      <h2 className="card__title">{tr("Осмотр")}</h2>
      <InspectionForm hive={h} onDone={() => navigate(`/hives/${h.id}`, { replace: true })}
        doneActions={<>
          <Link className="btn btn--primary btn--block" to="/scan" replace><Icon name="scan" size={18} />{tr("Следующий улей")}</Link>
          <Link className="btn btn--secondary btn--block" to={`/hives/${h.id}/check`} replace>{tr("Итог по улью")}</Link>
          <Link className="btn btn--ghost btn--block" to={`/hives/${h.id}`} replace>{tr("Паспорт улья")}</Link>
        </>} />
    </div>
  )
}
