/** The app: started by main.tsx once the language catalog is loaded. */
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient } from '@tanstack/react-query'
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client'
import { CACHE_MAX_AGE, cachedUserId, persister, shouldPersist } from './services/offlineCache'
import { App } from './App'
import { AuthProvider } from './hooks/useAuth'
import { initTelegram } from './services/telegram'
import { initPwa } from './services/pwa'
import { ApiError, setPaymentRequiredHandler } from './api/client'
import { loadBranding, markSubscriptionEnded } from './services/branding'
import '@fontsource/forum/cyrillic-400.css'
import '@fontsource/forum/cyrillic-ext-400.css' // Tajik letters ӣ ӯ ҳ қ ғ ҷ
import '@fontsource/forum/latin-400.css'
import '@fontsource-variable/manrope/index.css'
import '@fontsource-variable/onest/index.css' // fallback for Tajik letters; the browser downloads only the subsets it needs
import './styles.css'
import { getLang } from './i18n'
import { initConnection } from './services/connection'
import { flushOutbox } from './services/outbox'

initTelegram()
initPwa()
document.documentElement.lang = getLang()
setPaymentRequiredHandler(markSubscriptionEnded)

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: CACHE_MAX_AGE, // kept for the offline cache
      networkMode: 'offlineFirst', // show the saved data at once; no connection is not an error to wait on
      retry: (count, err) => !(err instanceof ApiError && err.status >= 400 && err.status < 500) && count < 2,
      refetchOnWindowFocus: false,
    },
    // saving must never wait for the connection: field records go to the outbox (services/outbox)
    mutations: { networkMode: 'always' },
  },
})

// Back online at the apiary: send what was saved on the phone, then refresh the screens
initConnection(() => {
  void flushOutbox().then((sent) => { if (sent) void queryClient.invalidateQueries() })
})

// The brand (name, logo, colour) and the subscription state come before the first screen
void loadBranding().then(() => createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <PersistQueryClientProvider client={queryClient}
      persistOptions={{ persister, maxAge: CACHE_MAX_AGE, buster: cachedUserId(), dehydrateOptions: { shouldDehydrateQuery: shouldPersist } }}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </PersistQueryClientProvider>
  </StrictMode>,
))
