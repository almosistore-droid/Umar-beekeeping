import { useMutation, useQueryClient } from '@tanstack/react-query'
import { haptic } from '../../services/telegram'
import type { Hive } from '../../types/api'

/** Shared save handler for hive records: updates the hive card in place and refreshes related lists. */
export function useHiveRecordMutation<R extends { hive: Hive } | Hive, V = void>(
  hive: Hive,
  fn: (vars: V) => Promise<R>,
  onSuccess: (res: R) => void,
) {
  const qc = useQueryClient()
  return useMutation<R, Error, V>({
    mutationFn: fn,
    onSuccess: (res) => {
      haptic('success')
      const updated = 'hive' in res ? res.hive : res
      qc.setQueryData(['hive', hive.id], updated)
      for (const key of ['hives', 'hive-timeline', 'hive-history', 'hive-inspections', 'hive-cases', 'hive-tasks', 'tasks', 'attention', 'hive-honey', 'honey-stats', 'hive-winterings', 'queens', 'hive-families', 'hive-queens', 'apiaries']) {
        qc.invalidateQueries({ queryKey: [key] })
      }
      onSuccess(res)
    },
    onError: () => haptic('error'),
  })
}
