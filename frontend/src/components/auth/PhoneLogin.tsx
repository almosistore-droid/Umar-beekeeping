import { useCallback, useEffect, useRef, useState } from 'react'
import { authApi } from '../../api/auth'
import { ApiError } from '../../api/client'
import { useAuth } from '../../hooks/useAuth'
import { deviceName } from '../../services/device'
import type { LoginCode } from '../../types/api'
import { Icon } from '../Icon'
import { InstallHint } from './InstallHint'
import { PasswordLoginForm } from './PasswordForms'
import { tr } from '../../i18n'
import { DeveloperCredit } from '../DeveloperCredit'
import { useBranding } from '../../services/branding'

const POLL_EVERY_MS = 2000
// Ask for a fresh code a bit before the old one expires, so the button always opens a valid one
const REFRESH_BEFORE_S = 30

type Phase = 'preparing' | 'ready' | 'waiting' | 'denied' | 'expired' | 'failed'

/**
 * Login outside Telegram. With a login and password from the admin, or through the bot: the button opens
 * the bot with a one-time code, the user taps «Войти» there and comes back while this screen asks the
 * server whether the code was confirmed.
 */
export function PhoneLogin({ message }: { message?: string }) {
  const brand = useBranding()
  const { completeDeviceLogin } = useAuth()
  const [code, setCode] = useState<LoginCode | null>(null)
  const [phase, setPhase] = useState<Phase>('preparing')
  const [error, setError] = useState<string | null>(null)
  // The server has no bot configured: only the password login is offered
  const [telegramOff, setTelegramOff] = useState(false)
  const codeRef = useRef<LoginCode | null>(null)

  const prepare = useCallback(async () => {
    setPhase('preparing')
    setError(null)
    try {
      const fresh = await authApi.createLoginCode(deviceName())
      codeRef.current = fresh
      setCode(fresh)
      setPhase('ready')
    } catch (e) {
      if (e instanceof ApiError && e.status === 503) { setTelegramOff(true); return }
      setError(e instanceof ApiError ? e.message : tr("Не удалось войти"))
      setPhase('failed')
    }
  }, [])

  useEffect(() => { void prepare() }, [prepare])

  // A code lives 5 minutes: renew it while the user hasn't tapped the button yet
  useEffect(() => {
    if (phase !== 'ready' || !code) return
    const t = setTimeout(() => void prepare(), Math.max(code.expires_in - REFRESH_BEFORE_S, 10) * 1000)
    return () => clearTimeout(t)
  }, [phase, code, prepare])

  const check = useCallback(async () => {
    const current = codeRef.current
    if (!current) return
    try {
      const res = await authApi.pollLoginCode(current.code, current.poll_secret)
      if (codeRef.current !== current) return
      if (res.status === 'ok') { codeRef.current = null; completeDeviceLogin(res) }
      else if (res.status === 'denied') { codeRef.current = null; setPhase('denied') }
      else if (res.status === 'expired') { codeRef.current = null; setPhase('expired') }
    } catch (e) {
      if (e instanceof ApiError && e.status > 0) { codeRef.current = null; setError(e.message); setPhase('failed') }
      // no connection for a moment: keep waiting
    }
  }, [completeDeviceLogin])

  // While waiting: ask every 2 s, and at once when the user comes back from Telegram
  useEffect(() => {
    if (phase !== 'waiting') return
    const timer = setInterval(() => void check(), POLL_EVERY_MS)
    const onVisible = () => { if (document.visibilityState === 'visible') void check() }
    document.addEventListener('visibilitychange', onVisible)
    window.addEventListener('focus', onVisible)
    return () => {
      clearInterval(timer)
      document.removeEventListener('visibilitychange', onVisible)
      window.removeEventListener('focus', onVisible)
    }
  }, [phase, check])

  const appLink = code ? `tg://resolve?domain=${code.bot_username}&start=login_${code.code}` : undefined

  const telegramBlock = phase === 'waiting' ? (
    <div className="login__wait" role="status">
      <span className="login__spinner" aria-hidden />
      <b>{tr("Подтвердите вход в Telegram")}</b>
      <span className="hint small">{tr("В чате с ботом нажмите «Войти» и вернитесь сюда — вход выполнится сам.")}</span>
      <a className="btn btn--ghost btn--block" href={code?.bot_link} target="_blank" rel="noopener noreferrer">
        {tr("Открыть Telegram ещё раз")}
      </a>
    </div>
  ) : (
    <>
      {(phase === 'denied' || phase === 'expired' || phase === 'failed') && (
        <p className="warn-box small" role="alert">
          {phase === 'denied' ? tr("Вход отменён в Telegram.")
            : phase === 'expired' ? tr("Время на подтверждение вышло. Попробуйте ещё раз.")
            : error}
        </p>
      )}
      {phase === 'ready' && code ? (
        <a className="btn btn--secondary btn--block login__tg" href={appLink} onClick={() => setPhase('waiting')}>
          <Icon name="send" size={20} />{tr("Войти через Telegram")}
        </a>
      ) : (
        <button type="button" className="btn btn--secondary btn--block" disabled={phase === 'preparing'}
          onClick={() => void prepare()}>
          {phase === 'preparing' ? tr("Подготовка…") : tr("Повторить")}
        </button>
      )}
      <p className="hint small">{tr("Через Telegram пароль не нужен: откроется бот, нажмите в нём «Войти».")}</p>
    </>
  )

  return (
    <div className="state login">
      <img className="state__logo" src={brand.logo_url} alt={brand.name} />
      <h2 className="state__title">{brand.name}</h2>
      <p className="hint">{tr("Учёт пасеки: ульи, матки, осмотры, мёд и отчёты.")}</p>
      {message && <p className="warn-box small">{message}</p>}
      <PasswordLoginForm />
      {!telegramOff && (
        <>
          <div className="login__or"><span>{tr("или")}</span></div>
          {telegramBlock}
        </>
      )}
      <p className="hint small">{tr("Нет логина? Попросите администратора создать вам вход.")}</p>
      <InstallHint />
      <DeveloperCredit />
    </div>
  )
}
