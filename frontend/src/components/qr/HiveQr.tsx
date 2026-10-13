import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { qrApi } from '../../api/resources'
import { usePermissions } from '../../hooks/usePermissions'
import type { QrInfo } from '../../types/api'
import { formatDate } from '../../utils/labels'
import { Icon } from '../Icon'
import { ErrorBox, Sheet } from '../ui'
import { LabelsActions } from './LabelsActions'

export function DeepLinkWarning() {
  return (
    <p className="warn-box">
      Бот не указан в настройках сервера (<code>TELEGRAM_BOT_USERNAME</code>). Такой QR откроется только из сканера
      в приложении, а камера телефона его не узнает. Укажите бота <b>до печати</b> — напечатанный QR потом не меняется.
    </p>
  )
}

/** Compact card on the hive page; the full QR opens in a sheet. */
export function HiveQrCard({ hiveId }: { hiveId: string }) {
  const [open, setOpen] = useState(false)
  const qr = useQuery({ queryKey: ['qr', hiveId], queryFn: () => qrApi.get(hiveId) })
  return (
    <section className="card">
      <button type="button" className="qr-card" onClick={() => setOpen(true)} disabled={!qr.data}>
        <span className="qr-card__thumb">{qr.data ? <img src={qr.data.svg_data_uri} alt="" /> : <Icon name="qr" />}</span>
        <span className="qr-card__text">
          <span className="card__title">QR-код улья</span>
          <span className="hint small">
            {qr.data ? (qr.data.print_count ? `Напечатан ${qr.data.print_count} р., последний раз ${formatDate(qr.data.last_printed_at!)}` : 'Ещё не печатался') : 'Загрузка…'}
          </span>
        </span>
        <span className="chevron">›</span>
      </button>
      <ErrorBox error={qr.error} />
      <Sheet open={open} title="QR-код улья" onClose={() => setOpen(false)}>
        {open && qr.data && <QrSheet qr={qr.data} />}
      </Sheet>
    </section>
  )
}

export function QrSheet({ qr }: { qr: QrInfo }) {
  const { canWrite } = usePermissions()
  return (
    <div className="form">
      <figure className="qr-big">
        <img src={qr.svg_data_uri} alt={`QR-код улья №${qr.hive_number}`} />
        <figcaption>
          <b>Улей №{qr.hive_number}</b>
          <span className="hint small">{qr.apiary_name}</span>
        </figcaption>
      </figure>
      {!qr.deep_link_ready && <DeepLinkWarning />}
      <p className="hint small">
        QR постоянный: он не изменится при смене номера, матки, семьи или пасеки. Внутри — только идентификатор улья.
      </p>
      {qr.deep_link && <p className="qr-link small"><span className="hint">Ссылка: </span>{qr.deep_link}</p>}
      {canWrite
        ? <LabelsActions request={{ hive_ids: [qr.hive_id] }} />
        : <p className="hint small">Печать доступна пчеловоду и помощнику.</p>}
      {canWrite && <Link className="link small" to="/qr-labels">Наклейки для всей пасеки →</Link>}
    </div>
  )
}
