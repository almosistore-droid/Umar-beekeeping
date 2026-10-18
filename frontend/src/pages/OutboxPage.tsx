import { useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { MessageView } from '../components/StateViews'
import { flushOutbox, removeItem, retryItem, useOutbox, type OutboxItem } from '../services/outbox'
import { formatDateTime } from '../utils/labels'
import { tr } from '../i18n'

const KIND: Record<OutboxItem['kind'], string> = {
  inspection: tr("Осмотр"), feeding: tr("Подкормка"), treatment: tr("Обработка"),
}

/** Records saved on the phone without internet: waiting, being sent, or refused by the server. */
export function OutboxPage() {
  const { items, online, sending } = useOutbox()
  const qc = useQueryClient()
  const send = () => { void flushOutbox().then((n) => { if (n) void qc.invalidateQueries() }) }
  return (
    <div className="page">
      <h1 className="page__title">{tr("Сохранено в телефоне")}</h1>
      <p className="hint">{online
        ? tr("Связь есть: записи отправляются сами. Если запись не принята — прочитайте причину и решите, что с ней делать.")
        : tr("Сейчас нет связи. Записи хранятся в телефоне и отправятся сами, когда появится интернет. Не удаляйте приложение и не выходите из него до отправки.")}</p>
      {!items.length ? (
        <MessageView icon="inspect" title={tr("Всё отправлено")} text={tr("В телефоне нет неотправленных записей.")} />
      ) : (
        <section className="card card--list">
          {items.map((i) => (
            <div key={i.id} className="stock-row">
              <span className="stock-row__main">
                <b>{KIND[i.kind]}{i.hive_number ? ` · ${tr("улей №{0}", i.hive_number)}` : ''}</b>
                <span className="small hint">{formatDateTime(i.created_at)}</span>
                {i.error && <span className="small" style={{ color: 'var(--ember)' }}>{i.error}</span>}
                {i.error && (
                  <span className="outbox-actions">
                    <button type="button" className="btn btn--ghost btn--sm" onClick={() => { retryItem(i.id); send() }}>{tr("Повторить")}</button>
                    <Link className="btn btn--ghost btn--sm" to={`/hives/${i.hive_id}`}>{tr("Улей")}</Link>
                    <button type="button" className="btn btn--ghost btn--sm"
                      onClick={() => { if (window.confirm(tr("Удалить эту запись с телефона? На сервер она не попадёт."))) removeItem(i.id) }}>
                      {tr("Удалить")}
                    </button>
                  </span>
                )}
              </span>
              {!i.error && <span className="small hint">{sending ? tr("отправка…") : tr("ждёт")}</span>}
            </div>
          ))}
        </section>
      )}
      {online && items.some((i) => !i.error) && (
        <button type="button" className="btn btn--primary btn--block" disabled={sending} onClick={send}>{tr("Отправить сейчас")}</button>
      )}
    </div>
  )
}
