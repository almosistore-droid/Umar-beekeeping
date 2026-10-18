import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, render, screen } from '@testing-library/react'
import { contactHref, SubscriptionBlocked, SubscriptionWarning } from '../components/Subscription'
import { DEFAULT_BRANDING, applyBranding, getBranding, hexToRgb, loadBranding, markSubscriptionEnded } from '../services/branding'
import { ApiError, api, setPaymentRequiredHandler } from '../api/client'

const asal = {
  ...DEFAULT_BRANDING,
  name: 'Asal Pro',
  subtitle: 'Пасека',
  color: '#3b82f4',
  color_light: '#4ca9ff',
  color_deep: '#2f68c3',
  logo_url: '/api/branding/logo.png?v=abc',
  subscription: { active: true, days_left: 3, contact: '@asal_support' },
}

function mockFetch(body: unknown, status = 200) {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })))
}

afterEach(() => {
  vi.unstubAllGlobals()
  setPaymentRequiredHandler(null)
})

describe('branding', () => {
  it('applies the brand of the installation: name, colours, title', async () => {
    mockFetch(asal)
    const b = await loadBranding()
    expect(b.name).toBe('Asal Pro')
    expect(document.title).toBe('Asal Pro')
    const style = document.documentElement.style
    expect(style.getPropertyValue('--gold')).toBe('#3b82f4')
    expect(style.getPropertyValue('--gold-deep')).toBe('#2f68c3')
    expect(style.getPropertyValue('--gold-rgb')).toBe('59, 130, 244')
  })

  it('keeps the defaults when the server cannot be reached', async () => {
    window.localStorage.clear()
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('offline') }))
    const b = await loadBranding()
    expect(b.name).toBe(DEFAULT_BRANDING.name)
    expect(b.subscription.active).toBe(true)
  })

  it('offline the brand seen last time is used', async () => {
    mockFetch(asal)
    await loadBranding()
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('offline') }))
    const b = await loadBranding()
    expect(b.name).toBe('Asal Pro')
    expect(b.subscription.active).toBe(true)
  })

  it('a 402 from any request closes the app', async () => {
    mockFetch(asal)
    await loadBranding()
    setPaymentRequiredHandler(markSubscriptionEnded)
    mockFetch({ detail: 'Подписка закончилась. Обратитесь к поставщику, чтобы продлить доступ.' }, 402)
    await expect(api('/api/hives')).rejects.toBeInstanceOf(ApiError)
    expect(getBranding().subscription.active).toBe(false)
  })

  it('blocked screen shows the brand and the supplier contact', () => {
    act(() => applyBranding(asal))
    mockFetch({ ...asal, subscription: { active: false, days_left: 0, contact: '+992 900 00 00 00' } })
    return loadBranding().then(() => {
      render(<SubscriptionBlocked />)
      expect(screen.getByText('Подписка закончилась')).toBeInTheDocument()
      expect(screen.getByRole('img')).toHaveAttribute('alt', 'Asal Pro')
      expect(screen.getByRole('link', { name: '+992 900 00 00 00' })).toHaveAttribute('href', 'tel:+992900000000')
    })
  })

  it('warning for the last days of the subscription', async () => {
    mockFetch(asal)
    await loadBranding()
    render(<SubscriptionWarning />)
    expect(screen.getByText(/через 3 дн\./)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '@asal_support' })).toHaveAttribute('href', 'https://t.me/asal_support')
  })

  it('no warning while plenty of days are left', async () => {
    mockFetch({ ...asal, subscription: { active: true, days_left: null, contact: null } })
    await loadBranding()
    const { container } = render(<SubscriptionWarning />)
    expect(container).toBeEmptyDOMElement()
  })

  it('contact links and colour parsing', () => {
    expect(contactHref('https://asal.tj')).toBe('https://asal.tj')
    expect(contactHref('info@asal.tj')).toBe('mailto:info@asal.tj')
    expect(contactHref('Умар')).toBeNull()
    expect(hexToRgb('#ffffff')).toBe('255, 255, 255')
    expect(hexToRgb('oops')).toBe('244, 194, 59')
  })
})
