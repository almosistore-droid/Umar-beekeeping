import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Icon } from '../components/Icon'
import { Field } from '../components/ui'
import { canScanQr, scanQr } from '../services/telegram'
import { tr } from '../i18n'

const SCAN_TEXT = tr("Наведите камеру на QR-код улья")

/** «Сканер» tab: Telegram's native camera scanner, plus manual entry for a computer. */
export function ScanPage() {
  const navigate = useNavigate()
  const available = canScanQr()
  const [manual, setManual] = useState('')
  const autoOpened = useRef(false)

  // replace: going back from the hive returns to where the user was before scanning
  const open = (code: string) => navigate(`/open?code=${encodeURIComponent(code.trim())}`, { replace: true })
  const scan = () => scanQr(SCAN_TEXT, open)

  // The scanner button in the bottom bar should open the camera straight away
  useEffect(() => {
    if (available && !autoOpened.current) {
      autoOpened.current = true
      scan()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [available])

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (manual.trim()) open(manual)
  }

  return (
    <div className="page">
      <h1 className="page__title">{tr("Сканер")}</h1>
      <section className="scan-hero">
        <span className="scan-hero__cell" aria-hidden><Icon name="scan" size={44} /></span>
        <p className="hint">{tr("Подойдите к улью и отсканируйте его QR-код — откроется паспорт улья.")}</p>
        {available
          ? <button type="button" className="btn btn--primary" onClick={scan}><Icon name="scan" size={20} />{tr("Сканировать улей")}</button>
          : <p className="warn-box small">{tr("Камера доступна, когда приложение открыто в Telegram на телефоне. Здесь можно вставить код вручную.")}</p>}
      </section>
      <form className="card form" onSubmit={submit}>
        <Field label={tr("Код или ссылка из QR")} hint={tr("Например hive_550e8400-… или ссылка t.me/…")}>
          <input className="input" value={manual} onChange={(e) => setManual(e.target.value)} autoComplete="off"
            autoCapitalize="off" spellCheck={false} placeholder="hive_…" />
        </Field>
        <button type="submit" className="btn btn--secondary" disabled={!manual.trim()}>{tr("Открыть улей")}</button>
      </form>
    </div>
  )
}
