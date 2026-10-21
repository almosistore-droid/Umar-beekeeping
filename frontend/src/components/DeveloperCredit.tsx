/**
 * «Developed by Fayziumar LLC» — the developer's mark at the bottom of «Ещё» and of the login screen.
 * Same in every installation (the brand of the client is separate). The mark: a honeycomb cell with a code sign.
 */
export function DeveloperCredit() {
  return (
    <footer className="dev-credit" aria-label="Developed by Fayziumar LLC">
      <svg className="dev-credit__mark" viewBox="0 0 360 360" width="40" height="40" aria-hidden="true">
        <defs>
          <linearGradient id="dev-gold" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#ffe7a1" /><stop offset="0.45" stopColor="#f4c23b" /><stop offset="1" stopColor="#a8740c" />
          </linearGradient>
        </defs>
        <path d="M180 16 L322 98 L322 262 L180 344 L38 262 L38 98 Z" fill="#1b150c" stroke="url(#dev-gold)" strokeWidth="14" strokeLinejoin="round" />
        <path d="M146 122 L96 180 L146 238" fill="none" stroke="url(#dev-gold)" strokeWidth="22" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M214 122 L264 180 L214 238" fill="none" stroke="url(#dev-gold)" strokeWidth="22" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M180 150 L206 165 L206 195 L180 210 L154 195 L154 165 Z" fill="url(#dev-gold)" />
      </svg>
      <span className="dev-credit__text">
        <span className="dev-credit__by">Developed by</span>
        <span className="dev-credit__name">Fayziumar <small>LLC</small></span>
      </span>
    </footer>
  )
}
