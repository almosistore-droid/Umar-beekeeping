import { useQuery } from '@tanstack/react-query'
import { stockApi } from '../../api/resources'
import { NormsForm } from '../../components/stock/forms'
import { LoadingView } from '../../components/StateViews'
import { ErrorBox } from '../../components/ui'
import { usePermissions } from '../../hooks/usePermissions'
import { haptic } from '../../services/telegram'
import { useState } from 'react'
import { tr } from '../../i18n'

/** «Нормы расхода»: how much wire and foundation one frame takes, how much sugar a litre of syrup. */
export function StockNormsPage() {
  const { canManage } = usePermissions()
  const norms = useQuery({ queryKey: ['stock', 'norms'], queryFn: stockApi.norms })
  const [saved, setSaved] = useState(false)
  return (
    <div className="page">
      <h1 className="page__title">{tr("Нормы расхода")}</h1>
      <p className="hint">{tr("По этим нормам приложение само списывает со склада проволоку и вощину при подготовке рамок и сахар при подкормке сиропом.")}</p>
      <ErrorBox error={norms.error} />
      {saved && <p className="ok-box small" role="status">{tr("Нормы сохранены. Уже сделанные записи не пересчитываются.")}</p>}
      {norms.isLoading ? <LoadingView /> : norms.data && (
        <section className="card">
          <NormsForm key={norms.data.updated_at ?? ''} norms={norms.data} canEdit={canManage}
            onDone={() => { haptic('success'); setSaved(true) }} />
          {!canManage && <p className="hint small">{tr("Нормы меняет пчеловод или администратор.")}</p>}
        </section>
      )}
    </div>
  )
}
