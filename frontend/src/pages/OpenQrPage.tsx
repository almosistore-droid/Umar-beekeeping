import { Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { qrApi } from '../api/resources'
import { LoadingView, MessageView } from '../components/StateViews'
import { ErrorBox } from '../components/ui'

/** Where a scanned code or a deep link (start_param) lands: opens the hive or explains why not. */
export function OpenQrPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const code = params.get('code') ?? ''
  const resolved = useQuery({ queryKey: ['qr-resolve', code], queryFn: () => qrApi.resolve(code), staleTime: 0, gcTime: 0 })
  const scanAgain = { label: 'Сканировать снова', onClick: () => navigate('/scan', { replace: true }) }

  if (resolved.isLoading) return <LoadingView text="Ищем улей…" />
  if (resolved.error) return <div className="page"><ErrorBox error={resolved.error} /></div>
  const r = resolved.data!

  // At the hive: choose «Осмотр» or «Проверка». Archived hives open their passport (history only).
  if (r.status === 'found') return <Navigate to={r.is_archived ? `/hives/${r.hive_id}` : `/hives/${r.hive_id}/visit`} replace />

  if (r.status === 'unknown') {
    return (
      <div className="page">
        <MessageView icon="hive" title="Улей не найден"
          text={r.can_register
            ? 'Этот QR ещё не привязан ни к одному улью. Можно зарегистрировать новый улей — наклейка на нём сразу заработает.'
            : 'Этот QR ещё не привязан ни к одному улью. Попросите администратора или пчеловода зарегистрировать улей.'}
          action={r.can_register ? { label: 'Зарегистрировать улей с этим QR', onClick: () => navigate(`/hives/new?qr=${r.hive_id}`, { replace: true }) } : scanAgain}
          secondary={r.can_register ? scanAgain : undefined} />
      </div>
    )
  }

  return (
    <div className="page">
      <MessageView icon="scan" title="Это не QR-код улья"
        text="В коде нет идентификатора улья. Отсканируйте наклейку, напечатанную в разделе «QR-наклейки»." action={scanAgain} />
    </div>
  )
}
