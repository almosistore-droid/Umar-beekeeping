import { useAuth } from './useAuth'
import { useBranding } from '../services/branding'

/** Mirrors backend role groups (app/auth/dependencies.py). The backend still enforces them. */
export function usePermissions() {
  const role = useAuth().user?.role
  const adminInApp = useBranding().admin_in_app !== false
  return {
    canManage: role === 'ADMIN' || role === 'BEEKEEPER',
    canWrite: role === 'ADMIN' || role === 'BEEKEEPER' || role === 'ASSISTANT',
    isAdmin: role === 'ADMIN',
    /** users, invitations, passwords, activity log — unless the owner keeps them in the owner panel */
    canAdminister: role === 'ADMIN' && adminInApp,
  }
}
