// Rating per game of a Road to Final card as small bars. Games that are not switched on yet stay empty.
const height = (mr) => Math.max(8, ((mr - 60) / 39) * 100)

export default function FormBars({ road }) {
  const aria = road.games.map((g) => `${g.label}: ${g.mr ?? 'open'}`).join(', ')
  return (
    <div className="form">
      <div className="form-head">
        <span>MR per game</span>
        {road.trend != null && (
          <span className={`trend ${road.trend < 0 ? 'down' : ''}`}>
            {road.trend < 0 ? '▼' : '▲'} {road.trend > 0 ? '+' : ''}
            {road.trend}
          </span>
        )}
      </div>
      <div className="form-bars" role="img" aria-label={`MR per game. ${aria}`} style={{ '--n': road.games.length }}>
        {road.games.map((g) =>
          g.mr == null ? (
            <div key={g.game_id} className="b empty">
              <i style={{ '--h': '30%' }} />
            </div>
          ) : (
            <div key={g.game_id} className="b">
              <span>{g.mr}</span>
              <i style={{ '--h': `${height(g.mr)}%` }} />
            </div>
          ),
        )}
      </div>
      <div className="form-labels" aria-hidden="true" style={{ '--n': road.games.length }}>
        {road.games.map((g) => (
          <span key={g.game_id}>{g.label}</span>
        ))}
      </div>
    </div>
  )
}
