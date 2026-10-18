import '@testing-library/jest-dom/vitest'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'
import { setCatalogForTests } from '../i18n'
import tg from '../i18n/tg.json'

setCatalogForTests('tg', tg as Record<string, string>)

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  vi.unstubAllEnvs()
  delete window.Telegram
})
