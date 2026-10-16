import { api } from './client'
import type { AuthResponse, LoginCode, LoginPoll, User } from '../types/api'

export const authApi = {
  loginWithTelegram: (initData: string) =>
    api<AuthResponse>('/api/auth/telegram', {
      method: 'POST',
      body: JSON.stringify({ init_data: initData }),
    }),
  me: () => api<User>('/api/auth/me'),
  // app on the phone outside Telegram
  createLoginCode: (deviceName: string) =>
    api<LoginCode>('/api/auth/login-codes', { method: 'POST', body: JSON.stringify({ device_name: deviceName || null }) }),
  pollLoginCode: (code: string, pollSecret: string) =>
    api<LoginPoll>('/api/auth/login-codes/poll', { method: 'POST', body: JSON.stringify({ code, poll_secret: pollSecret }) }),
  loginWithDevice: (deviceToken: string) =>
    api<AuthResponse>('/api/auth/device', { method: 'POST', body: JSON.stringify({ device_token: deviceToken }) }),
  passwordLogin: (login: string, password: string, deviceName: string) =>
    api<LoginPoll>('/api/auth/password', { method: 'POST', body: JSON.stringify({ login, password, device_name: deviceName || null }) }),
  changePassword: (currentPassword: string, newPassword: string) =>
    api<User>('/api/auth/me/password', { method: 'PUT', body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }) }),
  logout: (deviceToken: string) =>
    api<void>('/api/auth/logout', { method: 'POST', body: JSON.stringify({ device_token: deviceToken }) }),
  setLanguage: (language: 'ru' | 'tg') =>
    api<User>('/api/auth/me/language', { method: 'PUT', body: JSON.stringify({ language }) }),
}
