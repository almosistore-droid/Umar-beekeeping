import type { ReactNode } from 'react'
import { useMutation } from '@tanstack/react-query'
import { haptic, isInsideTelegram } from '../../services/telegram'
import { Icon } from '../Icon'
import { ErrorBox } from '../ui'
import { tr } from '../../i18n'

export function saveBlob(blob: Blob, filename: string) {
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
 * Inside Telegram on a phone a file cannot be downloaded, so the bot sends it to the user's chat
 * (primary there); in a browser the file is downloaded (primary there).
 */
export function DeliverButtons<S>({ fileLabel, send, download, sentNote, onDone, disabled }: {
  fileLabel: string
  send: () => Promise<S>
  download: () => Promise<{ blob: Blob; filename: string }>
  sentNote: (res: S) => ReactNode
  onDone?: () => void
  disabled?: boolean
}) {
  const inTelegram = isInsideTelegram()
  const sendM = useMutation({ mutationFn: send, onSuccess: () => { haptic('success'); onDone?.() }, onError: () => haptic('error') })
  const dlM = useMutation({
    mutationFn: download,
    onSuccess: ({ blob, filename }) => { saveBlob(blob, filename); haptic('success'); onDone?.() },
    onError: () => haptic('error'),
  })
  const pending = sendM.isPending || dlM.isPending
  const sendBtn = (
    <button key="send" type="button" className={`btn ${inTelegram ? 'btn--primary' : 'btn--secondary'}`} disabled={disabled || pending}
      onClick={() => { dlM.reset(); sendM.mutate() }}>
      <Icon name="send" size={18} />{sendM.isPending ? tr("Отправляем…") : tr("Отправить {0} в чат", fileLabel)}
    </button>
  )
  const downloadBtn = (
    <button key="download" type="button" className={`btn ${inTelegram ? 'btn--secondary' : 'btn--primary'}`} disabled={disabled || pending}
      onClick={() => { sendM.reset(); dlM.mutate() }}>
      <Icon name="download" size={18} />{dlM.isPending ? tr("Готовим…") : tr("Скачать {0}", fileLabel)}
    </button>
  )
  return (
    <div className="labels-actions">
      <ErrorBox error={sendM.error ?? dlM.error} />
      {sendM.data !== undefined && <p className="ok-box" role="status">{sentNote(sendM.data)}</p>}
      {inTelegram ? [sendBtn, downloadBtn] : [downloadBtn, sendBtn]}
    </div>
  )
}
