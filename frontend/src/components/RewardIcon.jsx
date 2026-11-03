// A consistent outline style for the reward milestones, independent of platform emoji fonts.
const ICONS = {
  soda: <><path d="M6 7h12l-2 14H8L6 7Z" /><path d="m12 7 1-5h5M6 11h12" /></>,
  pizza: <><path d="M4 5a21 21 0 0 1 16 0L12 22 4 5Z" /><path d="M5.5 8a17 17 0 0 1 13 0" /><circle cx="10" cy="12" r="1" /><circle cx="14" cy="10.5" r="1" /><circle cx="12" cy="16" r="1" /></>,
  merch: <><path d="M3 3h8l10 10a2 2 0 0 1 0 3l-5 5a2 2 0 0 1-3 0L3 11V3Z" /><circle cx="7.5" cy="7.5" r="1" /><path d="m11 17 6-6" /><circle cx="11.5" cy="11.5" r=".7" /><circle cx="16.5" cy="16.5" r=".7" /></>,
  scarf: <><path d="M7 3h10v5H7zM8 8v12h5V8m0 0 4 11 4-2-4-9M8 20v2m2.5-2v2M13 20v2m4-3 1 2m1-3 1 2m1-3 1 2" /><path d="M8 12h5m-5 4h5" /></>,
  'time-out': <><path d="M3 4v5a3 3 0 0 0 6 0V4M6 4v17m12-17c-3 2-4 5-4 9h4m0-9v17" /></>,
  jersey: <><path d="m8 3-6 4 3 5 3-2v11h8V10l3 2 3-5-6-4a4 4 0 0 1-8 0Z" /><path d="M10 14h4m-3-3h2v6" /></>,
}

export default function RewardIcon({ id }) {
  return (
    <svg className="reward-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      {ICONS[id] ?? <><rect x="3" y="7" width="18" height="14" rx="2" /><path d="M3 11h18M12 7v14m0-14C5 7 5 2 8 2c2 0 4 5 4 5Zm0 0c7 0 7-5 4-5-2 0-4 5-4 5Z" /></>}
    </svg>
  )
}
