import { Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { qrApi } from '../api/resources'
import { useOutbox } from '../services/outbox'
import type { Hive } from '../types/api'

const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i
import { LoadingView, MessageView } from '../components/StateViews'
import { ErrorBox } from '../components/ui'
import { tr } from '../i18n'

/** Where a scanned code or a deep link (start_param) lands: opens the hive or explains why not. */
export function OpenQrPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const code = params.get('code') ?? ''
  const resolved = useQuery({ queryKey: ['qr-resolve', code], queryFn: () => qrApi.resolve(code), staleTime: 0, gcTime: 0 })
  const scanAgain = { label: tr("Сканировать снова"), onClick: () => navigate('/scan', { replace: true }) }
  const { online } = useOutbox()
  const qc = useQueryClient()

  // No connection at the apiary: the hive id is inside the code; open it from the phone's copy
  if (!online && !resolved.data) {
    const id = UUID.exec(code)?.[0]?.toLowerCase()
    const cached = id ? qc.getQueryData<Hive>(['hive', id]) : undefined
    if (cached) return <Navigate to={cached.is_archived ? `/hives/${id}` : `/hives/${id}/visit`} replace />
    return (
      <div className="page">
        <MessageView icon="scan" title={id ? tr("Улей не загружен в телефон") : tr("Это не QR-код улья")}
          text={id ? tr("Нет связи, а этот улей ещё не открывался на телефоне. Когда появится интернет, приложение само загрузит все ульи для работы без связи.")
            : tr("В коде нет идентификатора улья. Отсканируйте наклейку, напечатанную в разделе «QR-наклейки».")}
          action={scanAgain} />
      </div>
    )
  }

  if (resolved.isLoading) return <LoadingView text={tr("Ищем улей…")} />
  if (resolved.error) return <div className="page"><ErrorBox error={resolved.error} /></div>
  const r = resolved.data!

  // At the hive: choose «Осмотр» or «Проверка». Archived hives open their passport (history only).
  if (r.status === 'found') return <Navigate to={r.is_archived ? `/hives/${r.hive_id}` : `/hives/${r.hive_id}/visit`} replace />

  if (r.status === 'unknown') {
    return (
      <div className="page">
        <MessageView icon="hive" title={tr("Улей не найден")}
          text={r.can_register
            ? tr("Этот QR ещё не привязан ни к одному улью. Можно зарегистрировать новый улей — наклейка на нём сразу заработает.")
            : tr("Этот QR ещё не привязан ни к одному улью. Попросите администратора или пчеловода зарегистрировать улей.")}
          action={r.can_register ? { label: tr("Зарегистрировать улей с этим QR"), onClick: () => navigate(`/hives/new?qr=${r.hive_id}`, { replace: true }) } : scanAgain}
          secondary={r.can_register ? scanAgain : undefined} />
      </div>
    )
  }

  return (
    <div className="page">
      <MessageView icon="scan" title={tr("Это не QR-код улья")}
        text={tr("В коде нет идентификатора улья. Отсканируйте наклейку, напечатанную в разделе «QR-наклейки».")} action={scanAgain} />
    </div>
  )
}
