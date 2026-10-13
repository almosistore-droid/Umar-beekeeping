import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { healthApi } from '../api/resources'
import { ErrorBox } from '../components/ui'
import { LoadingView, MessageView } from '../components/StateViews'
import { usePermissions } from '../hooks/usePermissions'
import { haptic } from '../services/telegram'
import { formatDate, todayIso } from '../utils/labels'

/** All open reminders across hives, soonest first. */
export function TasksPage() {
  const { canWrite } = usePermissions()
  const qc = useQueryClient()
  const tasks = useQuery({ queryKey: ['tasks', 'open'], queryFn: () => healthApi.tasks() })
  const done = useMutation({
    mutationFn: healthApi.completeTask,
    onSuccess: () => { haptic('success'); for (const k of ['tasks', 'hive-tasks', 'attention']) qc.invalidateQueries({ queryKey: [k] }) },
    onError: () => haptic('error'),
  })
  const today = todayIso()

  return (
    <div className="page">
      <h1 className="page__title">Напоминания</h1>
      <ErrorBox error={tasks.error ?? done.error} />
      {tasks.isLoading ? <LoadingView /> : !tasks.data?.length ? (
        <MessageView icon="treat" title="Напоминаний нет" text="Они появляются, когда при обработке или подкормке указана следующая дата." />
      ) : (
        <section className="card">
          {tasks.data.map((t) => (
            <div key={t.id} className="reminder">
              <div className="reminder__body">
                <div>{t.title}</div>
                <div className={`reminder__due${t.due_date < today ? ' is-overdue' : ''}`}>
                  {t.due_date < today ? 'Просрочено: ' : t.due_date === today ? 'Сегодня: ' : 'К '}{formatDate(t.due_date)}
                  {t.hive_id && <>, <Link className="link" to={`/hives/${t.hive_id}`}>улей №{t.hive_number}</Link></>}
                </div>
              </div>
              {canWrite && <button type="button" className="btn btn--ghost btn--sm" disabled={done.isPending} onClick={() => done.mutate(t.id)}>Готово</button>}
            </div>
          ))}
        </section>
      )}
    </div>
  )
}
