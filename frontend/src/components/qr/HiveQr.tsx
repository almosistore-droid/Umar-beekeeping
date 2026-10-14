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
import { tr } from '../../i18n'

export function DeepLinkWarning() {
  return (
    <p className="warn-box">{tr("Бот не указан в настройках сервера (")}<code>TELEGRAM_BOT_USERNAME</code>{tr("). Такой QR откроется только из сканера в приложении, а камера телефона его не узнает. Укажите бота")}{" "}<b>{tr("до печати")}</b>{" "}{tr("— напечатанный QR потом не меняется.")}</p>
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
          <span className="card__title">{tr("QR-код улья")}</span>
          <span className="hint small">
            {qr.data ? (qr.data.print_count ? tr("Напечатан {0} р., последний раз {1}", qr.data.print_count, formatDate(qr.data.last_printed_at!)) : tr("Ещё не печатался")) : tr("Загрузка…")}
          </span>
        </span>
        <span className="chevron">›</span>
      </button>
      <ErrorBox error={qr.error} />
      <Sheet open={open} title={tr("QR-код улья")} onClose={() => setOpen(false)}>
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
        <img src={qr.svg_data_uri} alt={tr("QR-код улья №{0}", qr.hive_number)} />
        <figcaption>
          <b>{tr("Улей №{0}", qr.hive_number)}</b>
          <span className="hint small">{qr.apiary_name}</span>
        </figcaption>
      </figure>
      {!qr.deep_link_ready && <DeepLinkWarning />}
      <p className="hint small">{tr("QR постоянный: он не изменится при смене номера, матки, семьи или пасеки. Внутри — только идентификатор улья.")}</p>
      {qr.deep_link && <p className="qr-link small"><span className="hint">{tr("Ссылка:")}{" "}</span>{qr.deep_link}</p>}
      {canWrite
        ? <LabelsActions request={{ hive_ids: [qr.hive_id] }} />
        : <p className="hint small">{tr("Печать доступна пчеловоду и помощнику.")}</p>}
      {canWrite && <Link className="link small" to="/qr-labels">{tr("Наклейки для всей пасеки →")}</Link>}
    </div>
  )
}
