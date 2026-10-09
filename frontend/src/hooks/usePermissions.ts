import { useAuth } from './useAuth'

/** Mirrors backend role groups (app/auth/dependencies.py). The backend still enforces them. */
export function usePermissions() {
  const role = useAuth().user?.role
  return {
    canManage: role === 'ADMIN' || role === 'BEEKEEPER',
    canWrite: role === 'ADMIN' || role === 'BEEKEEPER' || role === 'ASSISTANT',
    isAdmin: role === 'ADMIN',
  }
}
