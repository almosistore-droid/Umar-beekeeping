/** Line icons drawn for the Fayzi Umar theme (24×24, stroke = currentColor). */
const PATHS = {
  home: <><path d="M4 10.5 12 4l8 6.5" /><path d="M6 9.5V20h12V9.5" /><path d="M10 20v-5h4v5" /></>,
  hive: <><path d="M12 3 19.5 7.3v9.4L12 21l-7.5-4.3V7.3z" /><path d="M8.5 10h7M8 13.5h8M8.5 17h7" /></>,
  scan: <><path d="M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3" /><path d="M8 8h3v3H8zM13 13h3v3h-3zM13 8h3M8 13v3h3" /></>,
  crown: <><path d="M4 8.5 8 12l4-6 4 6 4-3.5-1.6 9H5.6z" /><path d="M6 20h12" /></>,
  chart: <><path d="M4 20h16" /><path d="M7 16v-5M12 16V7M17 16v-8" /></>,
  menu: <><path d="M4 7h16M4 12h16M4 17h16" /></>,
  plus: <><path d="M12 5v14M5 12h14" /></>,
  edit: <><path d="M4 20h4L19 9l-4-4L4 16z" /><path d="m13.5 6.5 4 4" /></>,
  inspect: <><circle cx="10.5" cy="10.5" r="5.5" /><path d="m15 15 5 5" /></>,
  honey: <><path d="M7 9h10l-1 10.5a1.5 1.5 0 0 1-1.5 1.5h-5A1.5 1.5 0 0 1 8 19.5z" /><path d="M6 9h12M9 5h6l1 4H8z" /></>,
  health: <><path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z" /><path d="M9 11h6M12 8v6" /></>,
  treat: <><rect x="3.5" y="9" width="17" height="6" rx="3" transform="rotate(-35 12 12)" /><path d="m10 8.5 4 7" /></>,
  feed: <><path d="M4 11h16a8 8 0 0 1-16 0z" /><path d="M9 5c0 2 2 2 2 4M14 5c0 2 2 2 2 4" /></>,
  photo: <><rect x="3.5" y="6.5" width="17" height="13" rx="2" /><circle cx="12" cy="13" r="3.5" /><path d="M9 6.5 10.5 4h3L15 6.5" /></>,
  strong: <><path d="M5 19V13M10 19V9M15 19V6M20 19V3" /></>,
  weak: <><path d="M12 4 21 19H3z" /><path d="M12 10v4M12 16.5v.5" /></>,
  sick: <><path d="M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z" /><path d="M12 8v8M8 12h8" /></>,
  queenless: <><path d="M4 8.5 8 12l4-6 4 6 4-3.5-1.6 9H5.6z" /><path d="M3 3l18 18" /></>,
  apiary: <><path d="M3 20h18" /><path d="M5 20v-6l3.5-3 3.5 3v6M12 20v-6l3.5-3 3.5 3v6" /><path d="M12 5v2M8.5 6.5l1 1.5M15.5 6.5l-1 1.5" /></>,
  users: <><circle cx="9" cy="9" r="3.5" /><path d="M3 20a6 6 0 0 1 12 0" /><path d="M16 5.5a3.5 3.5 0 0 1 0 7M18 14.5a6 6 0 0 1 3 5.5" /></>,
  chevron: <><path d="m9 6 6 6-6 6" /></>,
  qr: <><rect x="4" y="4" width="6" height="6" rx="1" /><rect x="14" y="4" width="6" height="6" rx="1" /><rect x="4" y="14" width="6" height="6" rx="1" /><path d="M14 14h2v2h-2zM18 14h2M14 18v2M17 17h3v3h-3" /></>,
  send: <><path d="M21 3 10.5 13.5" /><path d="M21 3 14.5 21l-4-7.5L3 9.5z" /></>,
  download: <><path d="M12 4v11" /><path d="m7.5 10.5 4.5 4.5 4.5-4.5" /><path d="M5 19.5h14" /></>,
} as const

export type IconName = keyof typeof PATHS

export function Icon({ name, size = 24, className }: { name: IconName; size?: number; className?: string }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      {PATHS[name]}
    </svg>
  )
}
