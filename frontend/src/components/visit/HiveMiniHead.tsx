import type { ReactNode } from 'react'
import { tr } from '../../i18n'

/** Compact hive header for the field screens (choice, inspection, check). */
export function HiveMiniHead({ number, apiary, children }: { number: string; apiary: string; children?: ReactNode }) {
  return (
    <header className="hive-head">
      <div className="hive-head__title">
        <span className={`hive-head__badge${number.length > 3 ? ' hive-head__badge--long' : ''}`} aria-hidden>{number}</span>
        <div>
          <h1 className="page__title">{tr("Улей №{0}", number)}</h1>
          <p className="hint">{apiary}</p>
        </div>
      </div>
      {children}
    </header>
  )
}
