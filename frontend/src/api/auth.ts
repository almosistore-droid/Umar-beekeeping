import { api } from './client'
import type { AuthResponse, User } from '../types/api'

export const authApi = {
  loginWithTelegram: (initData: string) =>
    api<AuthResponse>('/api/auth/telegram', {
      method: 'POST',
      body: JSON.stringify({ init_data: initData }),
    }),
  me: () => api<User>('/api/auth/me'),
}
