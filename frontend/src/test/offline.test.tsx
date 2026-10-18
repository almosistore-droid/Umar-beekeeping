import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'
import { setAccessToken } from '../api/client'
import { healthApi } from '../api/resources'
import { OfflineBar } from '../components/offline/OfflineBar'
import { OpenQrPage } from '../pages/OpenQrPage'
import { OutboxPage } from '../pages/OutboxPage'
import { flushOutbox, isQueued, outboxSnapshot, resetOutbox, setOnline } from '../services/outbox'
import type { Hive } from '../types/api'

vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({ state: { status: 'authenticated', offline: true }, user: { id: 'me', role: 'BEEKEEPER' } }),
}))

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
const HIVE = { id: '0b7c5a2e-6f0d-4b55-9a51-3c1b2b0f9e11', hive_number: '27' }

beforeEach(() => { resetOutbox(); setAccessToken('token') })
afterEach(() => { vi.restoreAllMocks(); setAccessToken(null) })

describe('outbox', () => {
  it('without a connection the feeding is kept on the phone and sent later once', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'))
    const res = await healthApi.feed(HIVE, { feed_type: 'SUGAR_SYRUP', quantity: 2, unit: 'L', fed_at: '2026-10-18' })
    expect(isQueued(res)).toBe(true)
    const [item] = outboxSnapshot().items
    expect(item.kind).toBe('feeding')
    expect(item.hive_number).toBe('27')
    expect(item.body.client_uid).toBeTruthy()
    expect(outboxSnapshot().online).toBe(false)

    // while offline the next record goes straight to the outbox (no waiting)
    fetchMock.mockClear()
    await healthApi.treat(HIVE, { medication: 'Бипин', treated_at: '2026-10-18' })
    expect(fetchMock).not.toHaveBeenCalled()
    expect(outboxSnapshot().items).toHaveLength(2)

    fetchMock.mockImplementation(async () => json({ feeding: {}, hive: {} }, 201))
    setOnline(true)
    expect(await flushOutbox()).toBe(2)
    expect(outboxSnapshot().items).toHaveLength(0)
    const sent = JSON.parse(String(fetchMock.mock.calls[0][1]!.body))
    expect(sent.client_uid).toBe(item.body.client_uid)
  })

  it('a refused record stays with the reason, others go on', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('offline'))
    await healthApi.feed(HIVE, { feed_type: 'CANDY', quantity: 1, unit: 'KG' })
    await healthApi.feed(HIVE, { feed_type: 'CANDY', quantity: 2, unit: 'KG' })
    let n = 0
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () =>
      (n++ === 0 ? json({ detail: 'Улей №27 в архиве — новые записи не добавляются' }, 409) : json({}, 201)))
    setOnline(true)
    expect(await flushOutbox()).toBe(1)
    const left = outboxSnapshot().items
    expect(left).toHaveLength(1)
    expect(left[0].error).toContain('в архиве')
  })

  it('stops at a connection problem and keeps the order', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('offline'))
    await healthApi.feed(HIVE, { feed_type: 'CANDY', quantity: 1, unit: 'KG' })
    await healthApi.feed(HIVE, { feed_type: 'CANDY', quantity: 2, unit: 'KG' })
    setOnline(true)
    expect(await flushOutbox()).toBe(0)
    expect(outboxSnapshot().items).toHaveLength(2)
    expect(outboxSnapshot().online).toBe(false)
  })

  it('is not sent before the person is signed in again', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('offline'))
    await healthApi.feed(HIVE, { feed_type: 'CANDY', quantity: 1, unit: 'KG' })
    setAccessToken(null)
    setOnline(true)
    expect(await flushOutbox()).toBe(0)
  })
})

function wrap(ui: React.ReactNode, path = '/', qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })) {
  return render(<QueryClientProvider client={qc}><MemoryRouter initialEntries={[path]}>{ui}</MemoryRouter></QueryClientProvider>)
}

describe('screens', () => {
  it('the bar tells there is no connection and how many records wait', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('offline'))
    await healthApi.feed(HIVE, { feed_type: 'CANDY', quantity: 1, unit: 'KG' })
    wrap(<OfflineBar />)
    expect(screen.getByText('Нет связи · в телефоне 1 — отправятся сами')).toBeInTheDocument()
  })

  it('the outbox page lists the records', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('offline'))
    await healthApi.inspect(HIVE, { strength: 'STRONG' } as never)
    wrap(<OutboxPage />)
    expect(screen.getByText('Осмотр · улей №27')).toBeInTheDocument()
    expect(screen.getByText(/Сейчас нет связи/)).toBeInTheDocument()
  })

  it('a scanned QR opens the hive from the phone copy when offline', async () => {
    setOnline(false)
    const qc = new QueryClient()
    qc.setQueryData(['hive', HIVE.id], { ...HIVE, is_archived: false } as unknown as Hive)
    wrap(<Routes>
      <Route path="/open" element={<OpenQrPage />} />
      <Route path="/hives/:id/visit" element={<p>visit page</p>} />
    </Routes>, `/open?code=${encodeURIComponent(`https://t.me/bee_bot?startapp=hive_${HIVE.id}`)}`, qc)
    await waitFor(() => expect(screen.getByText('visit page')).toBeInTheDocument())
  })

  it('an unknown hive offline explains it was not loaded', () => {
    setOnline(false)
    wrap(<Routes><Route path="/open" element={<OpenQrPage />} /></Routes>,
      '/open?code=hive_11111111-2222-4333-8444-555555555555')
    expect(screen.getByText('Улей не загружен в телефон')).toBeInTheDocument()
  })
})
