import { useEffect, useRef, useState } from 'react'
import { Icon } from '../Icon'
import { haptic } from '../../services/telegram'
import { tr } from '../../i18n'

/** The phone's camera can be used here (HTTPS page in a browser or the installed app). */
export function cameraAvailable(): boolean {
  return typeof navigator !== 'undefined' && !!navigator.mediaDevices?.getUserMedia && window.isSecureContext !== false
}

type Detect = (video: HTMLVideoElement) => Promise<string | null>

interface BarcodeDetectorLike { detect: (src: CanvasImageSource) => Promise<{ rawValue: string }[]> }
interface BarcodeDetectorCtor {
  new (opts: { formats: string[] }): BarcodeDetectorLike
  getSupportedFormats?: () => Promise<string[]>
}

/** Built-in BarcodeDetector (Android Chrome) or jsQR on video frames (iPhone Safari and others). */
async function makeDetector(canvas: HTMLCanvasElement): Promise<Detect> {
  const Native = (window as unknown as { BarcodeDetector?: BarcodeDetectorCtor }).BarcodeDetector
  if (Native) {
    try {
      const formats = (await Native.getSupportedFormats?.()) ?? ['qr_code']
      if (formats.includes('qr_code')) {
        const detector = new Native({ formats: ['qr_code'] })
        return async (video) => (await detector.detect(video))[0]?.rawValue ?? null
      }
    } catch {
      /* fall back to jsQR */
    }
  }
  const { default: jsQR } = await import('jsqr')
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  return async (video) => {
    if (!ctx || !video.videoWidth) return null
    const scale = Math.min(1, 720 / Math.max(video.videoWidth, video.videoHeight)) // faster on big cameras
    const w = Math.round(video.videoWidth * scale)
    const h = Math.round(video.videoHeight * scale)
    canvas.width = w
    canvas.height = h
    ctx.drawImage(video, 0, 0, w, h)
    const found = jsQR(ctx.getImageData(0, 0, w, h).data, w, h, { inversionAttempts: 'attemptBoth' })
    return found?.data || null
  }
}

function cameraError(e: unknown): string {
  const name = (e as { name?: string })?.name
  if (name === 'NotAllowedError' || name === 'SecurityError')
    return tr("Нет доступа к камере. Разрешите камеру для этого приложения в настройках телефона и попробуйте снова.")
  if (name === 'NotFoundError' || name === 'OverconstrainedError') return tr("Камера не найдена.")
  return tr("Не удалось включить камеру.")
}

/** Full-screen camera that reads one QR code and returns it. */
export function CameraScanner({ text, onResult, onClose }: {
  text: string
  onResult: (value: string) => void
  onClose: () => void
}) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [error, setError] = useState<string | null>(null)
  const resultRef = useRef(onResult)
  resultRef.current = onResult

  useEffect(() => {
    let stream: MediaStream | null = null
    let stopped = false
    let timer: ReturnType<typeof setTimeout> | undefined
    const stop = () => {
      stopped = true
      if (timer) clearTimeout(timer)
      stream?.getTracks().forEach((t) => t.stop())
    }
    void (async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false })
        if (stopped) { stop(); return }
        const video = videoRef.current!
        video.srcObject = stream
        await video.play()
        const detect = await makeDetector(canvasRef.current!)
        const tick = async () => {
          if (stopped) return
          let value: string | null = null
          try { value = await detect(video) } catch { /* a bad frame */ }
          if (stopped) return
          if (value) {
            stop()
            haptic('success')
            navigator.vibrate?.(60)
            resultRef.current(value)
            return
          }
          timer = setTimeout(() => void tick(), 180)
        }
        void tick()
      } catch (e) {
        if (!stopped) setError(cameraError(e))
      }
    })()
    return stop
  }, [])

  return (
    <div className="camera" role="dialog" aria-modal="true" aria-label={text}>
      <video ref={videoRef} className="camera__video" playsInline muted autoPlay />
      <canvas ref={canvasRef} hidden />
      <div className="camera__frame" aria-hidden />
      <p className="camera__text">{error ?? text}</p>
      <button type="button" className="camera__close" onClick={onClose} aria-label={tr("Закрыть")}>
        <Icon name="close" size={26} />
      </button>
    </div>
  )
}
