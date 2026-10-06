export type UserRole = 'ADMIN' | 'BEEKEEPER' | 'ASSISTANT' | 'VIEWER'

export interface User {
  id: string
  telegram_id: number
  username: string | null
  first_name: string | null
  last_name: string | null
  display_name: string
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: 'bearer'
  expires_in: number
  user: User
  start_param: string | null
}

export const ROLE_LABELS: Record<UserRole, string> = {
  ADMIN: 'Администратор',
  BEEKEEPER: 'Пчеловод',
  ASSISTANT: 'Помощник',
  VIEWER: 'Наблюдатель',
}
