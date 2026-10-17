import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
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

initTelegram()
initPwa()
document.documentElement.lang = getLang()
setPaymentRequiredHandler(markSubscriptionEnded)

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (count, err) => !(err instanceof ApiError && err.status >= 400 && err.status < 500) && count < 2,
      refetchOnWindowFocus: false,
    },
  },
})

// The brand (name, logo, colour) and the subscription state come before the first screen
void loadBranding().then(() => createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
))
