import { useQueryClient } from '@tanstack/react-query'
import { qrApi } from '../../api/resources'
import type { LabelsRequest } from '../../types/api'
import { plural } from '../../utils/plural'
import { DeliverButtons } from '../files/DeliverButtons'

/** QR label sheet: sent by the bot inside Telegram, downloaded in a browser. */
export function LabelsActions({ request, disabled }: { request: LabelsRequest; disabled?: boolean }) {
  const qc = useQueryClient()
  return (
    <DeliverButtons fileLabel="PDF" disabled={disabled}
      send={() => qrApi.sendLabels(request)}
      download={() => qrApi.downloadLabels(request)}
      onDone={() => ['qr', 'hive-timeline', 'hive-history'].forEach((k) => qc.invalidateQueries({ queryKey: [k] }))}
      sentNote={(r) => <>
        PDF ({r.labels} {plural(r.labels, 'наклейка', 'наклейки', 'наклеек')}) отправлен в чат с ботом.
        Перешлите его на компьютер или принтер и печатайте на A4 в масштабе 100%.
      </>} />
  )
}
