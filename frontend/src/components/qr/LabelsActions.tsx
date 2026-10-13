import { useMutation, useQueryClient } from '@tanstack/react-query'
import { qrApi } from '../../api/resources'
import { haptic, isInsideTelegram } from '../../services/telegram'
import type { LabelsRequest } from '../../types/api'
import { plural } from '../../utils/plural'
import { Icon } from '../Icon'
import { ErrorBox } from '../ui'

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 10_000)
}

/**
 * Inside Telegram on a phone a file cannot be downloaded, so the bot sends the PDF to the
 * user's chat (forward it to a printer or a computer). In a browser the PDF is downloaded.
 */
export function LabelsActions({ request, disabled }: { request: LabelsRequest; disabled?: boolean }) {
  const qc = useQueryClient()
  const inTelegram = isInsideTelegram()
  const onSuccess = () => {
    haptic('success')
    qc.invalidateQueries({ queryKey: ['qr'] })
    qc.invalidateQueries({ queryKey: ['hive-timeline'] })
    qc.invalidateQueries({ queryKey: ['history'] })
  }
  const send = useMutation({ mutationFn: () => qrApi.sendLabels(request), onSuccess, onError: () => haptic('error') })
  const download = useMutation({
    mutationFn: () => qrApi.downloadLabels(request),
    onSuccess: ({ blob, filename }) => { saveBlob(blob, filename); onSuccess() },
    onError: () => haptic('error'),
  })
  const pending = send.isPending || download.isPending
  const sendBtn = (
    <button type="button" className={`btn ${inTelegram ? 'btn--primary' : 'btn--secondary'}`} disabled={disabled || pending}
      onClick={() => { download.reset(); send.mutate() }}>
      <Icon name="send" size={18} />{send.isPending ? 'Отправляем…' : 'Отправить PDF в чат'}
    </button>
  )
  const downloadBtn = (
    <button type="button" className={`btn ${inTelegram ? 'btn--secondary' : 'btn--primary'}`} disabled={disabled || pending}
      onClick={() => { send.reset(); download.mutate() }}>
      <Icon name="download" size={18} />{download.isPending ? 'Готовим…' : 'Скачать PDF'}
    </button>
  )
  return (
    <div className="labels-actions">
      <ErrorBox error={send.error ?? download.error} />
      {send.data && (
        <p className="ok-box" role="status">
          PDF ({send.data.labels} {plural(send.data.labels, 'наклейка', 'наклейки', 'наклеек')}) отправлен в чат с ботом.
          Перешлите его на компьютер или принтер и печатайте на A4 в масштабе 100%.
        </p>
      )}
      {inTelegram ? <>{sendBtn}{downloadBtn}</> : <>{downloadBtn}{sendBtn}</>}
    </div>
  )
}
