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
  shield: <><path d="M12 3 19 6v5.5c0 4.3-2.9 8-7 9.5-4.1-1.5-7-5.2-7-9.5V6z" /><path d="m9 12 2 2 4-4" /></>,
  log: <><path d="M8 6h12M8 12h12M8 18h12" /><circle cx="4.5" cy="6" r="1" /><circle cx="4.5" cy="12" r="1" /><circle cx="4.5" cy="18" r="1" /></>,
  share: <><circle cx="18" cy="5.5" r="2.5" /><circle cx="6" cy="12" r="2.5" /><circle cx="18" cy="18.5" r="2.5" /><path d="m8.2 10.8 7.6-4M8.2 13.2l7.6 4" /></>,
  qr: <><rect x="4" y="4" width="6" height="6" rx="1" /><rect x="14" y="4" width="6" height="6" rx="1" /><rect x="4" y="14" width="6" height="6" rx="1" /><path d="M14 14h2v2h-2zM18 14h2M14 18v2M17 17h3v3h-3" /></>,
  send: <><path d="M21 3 10.5 13.5" /><path d="M21 3 14.5 21l-4-7.5L3 9.5z" /></>,
  wallet: <><path d="M4 7.5A2.5 2.5 0 0 1 6.5 5H18v3" /><rect x="4" y="8" width="16" height="11" rx="2" /><path d="M16 13.5h2" /></>,
  cart: <><path d="M3 4h2.5l2 11h10l2-7.5H6.4" /><circle cx="9.5" cy="19" r="1.3" /><circle cx="16.5" cy="19" r="1.3" /></>,
  receipt: <><path d="M6 3h12v18l-3-2-3 2-3-2-3 2z" /><path d="M9 8h6M9 12h6M9 16h3" /></>,
  box: <><path d="M3.5 7.5 12 3l8.5 4.5v9L12 21l-8.5-4.5z" /><path d="M3.5 7.5 12 12l8.5-4.5M12 12v9" /></>,
  phone: <><path d="M5 4h4l1.5 4.5-2.5 1.5a11 11 0 0 0 6 6l1.5-2.5L20 15v4a1 1 0 0 1-1 1A16 16 0 0 1 4 5a1 1 0 0 1 1-1z" /></>,
  coins: <><ellipse cx="9" cy="7" rx="5" ry="2.5" /><path d="M4 7v4c0 1.4 2.2 2.5 5 2.5s5-1.1 5-2.5V7" /><path d="M10 15.4c.9.4 2.1.6 3.5.6 2.8 0 5-1.1 5-2.5V10M14 10.6c2.6.1 4.5 1.1 4.5 2.4" /><path d="M4 11v4c0 1.4 2.2 2.5 5 2.5" /></>,
  close: <><path d="M6 6l12 12" /><path d="M18 6 6 18" /></>,
  iosShare: <><path d="M12 3.5v11" /><path d="m8 7.5 4-4 4 4" /><path d="M7 10.5H5.5v10h13v-10H17" /></>,
  mobile: <><rect x="7" y="2.5" width="10" height="19" rx="2.5" /><path d="M11 18.5h2" /></>,
  logout: <><path d="M14 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4" /><path d="m10 16-4-4 4-4" /><path d="M6 12h10" /></>,
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
