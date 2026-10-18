import { useMutation, useQueryClient } from '@tanstack/react-query'
import { haptic } from '../../services/telegram'
import { isQueued, type Queued } from '../../services/outbox'
import type { Hive } from '../../types/api'

/**
 * Shared save handler for hive records: updates the hive card in place and refreshes related lists.
 * A record saved without a connection comes back as `Queued` (kept on the phone, sent later).
 */
export function useHiveRecordMutation<R extends { hive: Hive } | Hive | Queued, V = void>(
  hive: Hive,
  fn: (vars: V) => Promise<R>,
  onSuccess: (res: R) => void,
) {
  const qc = useQueryClient()
  return useMutation<R, Error, V>({
    mutationFn: fn,
    onSuccess: (res) => {
      haptic('success')
      if (!isQueued(res)) {
        const updated = 'hive' in res ? res.hive : (res as Hive)
        qc.setQueryData(['hive', hive.id], updated)
        for (const key of ['hives', 'hive-timeline', 'hive-history', 'hive-check', 'hive-inspections', 'hive-cases', 'hive-tasks', 'tasks', 'attention', 'hive-honey', 'honey-stats', 'hive-winterings', 'queens', 'hive-families', 'hive-queens', 'apiaries', 'stock', 'stock-item', 'dashboard']) {
          qc.invalidateQueries({ queryKey: [key] })
        }
      }
      onSuccess(res)
    },
    onError: () => haptic('error'),
  })
}
