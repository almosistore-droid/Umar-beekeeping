import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../../hooks/useAuth'
import { prefetchForOffline } from '../../services/offlineCache'
import { flushOutbox, useOutbox } from '../../services/outbox'
import { tr } from '../../i18n'

/**
 * A thin line under the screen title area: no connection, records waiting to be sent, or refused records.
 * Also keeps the outbox moving and loads the hives into the phone for the next trip to the apiary.
 */
export function OfflineBar() {
  const { online, items, sending } = useOutbox()
  const { state } = useAuth()
  const qc = useQueryClient()
  const pending = items.filter((i) => !i.error).length
  const refused = items.length - pending
  const signedIn = state?.status === 'authenticated' && !state.offline

  useEffect(() => {
    if (!signedIn || !online) return
    void prefetchForOffline(qc)
    const send = () => { void flushOutbox().then((n) => { if (n) void qc.invalidateQueries() }) }
    send()
    const timer = setInterval(send, 30_000)
    return () => clearInterval(timer)
  }, [signedIn, online, qc])

  if (online && !items.length) return null
  if (!online) {
    return (
      <Link to="/outbox" className="offline-bar offline-bar--off" role="status">
        <span className="offline-bar__dot" aria-hidden />
        {pending
          ? tr("Нет связи · в телефоне {0} — отправятся сами", pending)
          : tr("Нет связи · записи сохраняются в телефоне")}
      </Link>
    )
  }
  return (
    <Link to="/outbox" className={`offline-bar${refused ? ' offline-bar--bad' : ''}`} role="status">
      <span className="offline-bar__dot" aria-hidden />
      {refused ? tr("Не отправлено: {0} — откройте, чтобы решить", refused)
        : sending ? tr("Отправляю сохранённые записи: {0}", pending) : tr("Ждут отправки: {0}", pending)}
    </Link>
  )
}
