// One half of the rink, drawn in metres with the attack going up: the net is at the top, the centre line at the bottom.
// Positions come from the backend as [x, y]: x is the distance from centre ice towards the net (goal line at 26, blue
// line at 7.1), y the distance from the middle. Dots move with a CSS transition, so a new position animates.
const GOAL_LINE = 26
const BLUE_LINE = 7.1
const BOARDS = 'M 0 30 L 0 8.5 A 8.5 8.5 0 0 1 8.5 0 L 21.5 0 A 8.5 8.5 0 0 1 30 8.5 L 30 30 Z'

export const toScreen = ([x, y]) => [15 + y, 30 - x]

const NET_Y = 30 - GOAL_LINE

// A player's name goes on the side away from the nearest other player, so two names close together don't overlap.
// The goalie's goes above, over the net.
function labelAbove(dot, players) {
  if (dot.kind === 'goalie') return true
  const [sx, sy] = toScreen(dot.at)
  const near = players
    .filter((o) => o !== dot && o.kind !== 'goalie')
    .map((o) => toScreen(o.at))
    .filter(([ox, oy]) => Math.hypot(ox - sx, oy - sy) < 4.5)
    .sort((a, b) => Math.hypot(a[0] - sx, a[1] - sy) - Math.hypot(b[0] - sx, b[1] - sy))[0]
  return near ? near[1] > sy : false
}

// dots: [{ id, at: [x, y], kind: 'skater' | 'goalie' | 'puck', side: 'you' | 'bot', label, active, onClick }]
export default function HalfRink({ dots, duration = 0, caption, outcome }) {
  const players = dots.filter((d) => d.kind !== 'puck')
  const ordered = [...players, ...dots.filter((d) => d.kind === 'puck')]
  return (
    <div className={`half-rink ${outcome ? `is-${outcome}` : ''}`}>
      <svg viewBox="-1 -1 32 32" role="img" aria-label="Half of the rink with the players as dots">
        <defs>
          <clipPath id="half-rink-clip">
            <path d={BOARDS} />
          </clipPath>
        </defs>
        <path d={BOARDS} className="rink-ice" />
        <g clipPath="url(#half-rink-clip)">
          <line x1="0" y1={NET_Y} x2="30" y2={NET_Y} className="rink-red thin" />
          <rect x="0" y={30 - BLUE_LINE - 0.15} width="30" height="0.3" className="rink-blue" />
          <rect x="0" y="29.85" width="30" height="0.3" className="rink-red-fill" />
          {[8, 22].map((cx) => (
            <g key={cx}>
              <circle cx={cx} cy="10" r="4.5" className="rink-red thin" />
              <circle cx={cx} cy="10" r="0.3" className="rink-red-fill" />
            </g>
          ))}
          <path d={`M 13.17 ${NET_Y} A 1.83 1.83 0 0 0 16.83 ${NET_Y} Z`} className="rink-crease" />
          <rect x="14.085" y={NET_Y - 1.1} width="1.83" height="1.1" className="rink-net" />
        </g>
        <path d={BOARDS} className="rink-boards" />
        {ordered.map((d) => {
          const [sx, sy] = toScreen(d.at)
          const style = { transform: `translate(${sx}px, ${sy}px)`, transition: `transform ${duration}ms ease-in-out` }
          if (d.kind === 'puck')
            return (
              <g key={d.id} style={style} className="rink-puck">
                <circle r="0.45" />
              </g>
            )
          return (
            <g
              key={d.id}
              style={style}
              className={`rink-dot ${d.side} ${d.kind} ${d.active ? 'active' : ''} ${d.onClick ? 'clickable' : ''}`}
              onClick={d.onClick}
            >
              {d.active && <circle r="1.9" className="rink-dot-ring" />}
              <circle r={d.kind === 'goalie' ? 1.25 : 1.05} />
              {d.label && (
                <text y={labelAbove(d, players) ? -1.6 : 2.5} className="rink-dot-label">
                  {d.label}
                </text>
              )}
            </g>
          )
        })}
      </svg>
      {caption && <p className="rink-caption" aria-live="polite">{caption}</p>}
    </div>
  )
}
