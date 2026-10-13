import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiariesApi, hivesApi, qrApi } from '../api/resources'
import { LabelsActions } from '../components/qr/LabelsActions'
import { DeepLinkWarning } from '../components/qr/HiveQr'
import { LoadingView } from '../components/StateViews'
import { Choice, ErrorBox, Stepper } from '../components/ui'
import { usePermissions } from '../hooks/usePermissions'
import { plural } from '../utils/plural'

/** Ещё → QR-наклейки: an A4 sheet for a whole apiary, plus blank labels for future hives. */
export function QrLabelsPage() {
  const { canWrite } = usePermissions()
  const apiaries = useQuery({ queryKey: ['apiaries'], queryFn: () => apiariesApi.list() })
  const status = useQuery({ queryKey: ['qr', 'status'], queryFn: qrApi.status })
  const [picked, setPicked] = useState<string | null>(null)
  const [blank, setBlank] = useState(0)
  const apiaryId = picked ?? apiaries.data?.[0]?.id ?? null
  const hives = useQuery({
    queryKey: ['hives', 'labels', apiaryId],
    queryFn: () => hivesApi.list({ apiary_id: apiaryId! }),
    enabled: !!apiaryId,
  })
  const count = hives.data?.total ?? 0
  const total = count + blank

  if (apiaries.isLoading) return <LoadingView />
  return (
    <div className="page">
      <h1 className="page__title">QR-наклейки</h1>
      <ErrorBox error={apiaries.error ?? hives.error} />
      {status.data && !status.data.deep_link_ready && <DeepLinkWarning />}
      <section className="card form">
        {(apiaries.data?.length ?? 0) > 1 && (
          <Choice label="Пасека" options={(apiaries.data ?? []).map((a) => ({ value: a.id, label: a.name }))}
            value={apiaryId} onChange={(v) => v && setPicked(v)} />
        )}
        <p className="hint">
          {hives.isLoading ? 'Считаем ульи…' : `${count} ${plural(count, 'улей', 'улья', 'ульев')} — по одной наклейке на каждый, по номерам.`}
        </p>
        <Stepper label="Пустые наклейки для новых ульев" value={blank} onChange={setBlank} max={60} />
        <p className="hint small">
          Пустую наклейку можно приклеить заранее: при первом сканировании приложение предложит зарегистрировать улей.
        </p>
      </section>
      <section className="card form">
        <h2 className="card__title">{total} {plural(total, 'наклейка', 'наклейки', 'наклеек')}, 12 на листе A4</h2>
        {canWrite
          ? <LabelsActions request={{ apiary_id: count ? apiaryId : null, blank_count: blank }} disabled={!total} />
          : <p className="hint">Печать доступна пчеловоду и помощнику.</p>}
      </section>
    </div>
  )
}
