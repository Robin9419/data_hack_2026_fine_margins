import { useTournament } from '../tournament'

// Fixed bar at the bottom of every page: the demo's time machine through the 2025 Spengler Cup. Before the
// tournament, one stop per gameday, after it. Moving on plays the games of the days passed.
export default function TimelineBar() {
  const { tournament, busy, setStage } = useTournament()
  if (!tournament) return null

  const stops = tournament.timeline
  const current = stops.findIndex((s) => s.state === 'current')

  return (
    <nav className="timeline" aria-label="Tournament timeline" data-tour="timeline">
      <div className="timeline-inner">
        <span className="timeline-title">
          Spengler Cup 2025
          <small>
            {tournament.packs_waiting > 0
              ? `${tournament.packs_waiting} ${tournament.packs_waiting === 1 ? 'pack' : 'packs'} to open`
              : 'Simulate the tournament'}
          </small>
        </span>
        <ol className="timeline-track" style={{ '--n': stops.length, '--at': current }}>
          {stops.map((s) => (
            <li key={s.id} className={`timeline-stop ${s.state}`}>
              <button
                type="button"
                disabled={busy}
                aria-current={s.state === 'current' ? 'step' : undefined}
                title={s.games ? `${s.sub}: ${s.games} ${s.games === 1 ? 'game' : 'games'}` : s.sub}
                onClick={() => setStage(s.id)}
              >
                <span className="timeline-dot" aria-hidden="true" />
                <strong>{s.label}</strong>
                <small>{s.sub}</small>
              </button>
            </li>
          ))}
        </ol>
      </div>
    </nav>
  )
}
