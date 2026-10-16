import { formatMatchDate } from '../format'
import { teamOf } from '../teams'

// Switches for the test data: official results and statistics of the other games of the 2025 Spengler Cup. Each game
// switched on adds its special cards (Player of the Match, Game Winner, Brick Wall, Record Breaker) to the gallery.
export default function TestDataPanel({ games, selected, onChange }) {
  const switchable = games.filter((g) => g.cards > 0).map((g) => g.id)
  const toggle = (id) => onChange(selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id])

  return (
    <details className="testdata">
      <summary>
        Test data: other games of the 2025 Spengler Cup
        <span className="muted"> · {selected.length} of {switchable.length} switched on</span>
      </summary>
      <p className="muted small">
        Only the final has Wisehockey data. For the other games the results, goals and player statistics come from the
        official game pages; the cards they add are marked TEST, have made-up match ratings and do not count towards
        your progress. Road to Final cards of the stars of each team grow with every game you switch on.
      </p>
      <div className="testdata-actions">
        <button type="button" className="filter-chip" onClick={() => onChange(switchable)}>
          All on
        </button>
        <button type="button" className="filter-chip" onClick={() => onChange([])}>
          All off
        </button>
      </div>
      <ul className="testgames">
        {games.map((g) => (
          <li key={g.id} className={selected.includes(g.id) ? 'on' : ''}>
            <label>
              <input
                type="checkbox"
                checked={selected.includes(g.id)}
                disabled={g.cards === 0}
                onChange={() => toggle(g.id)}
              />
              <span className="tg-when">
                {g.stage}
                <small>
                  {formatMatchDate(g.date)} · {g.start}
                </small>
              </span>
              <span className="tg-teams">
                <TeamMark name={g.home_team} />
                <strong>
                  {g.home_score}–{g.away_score}
                </strong>
                <TeamMark name={g.away_team} />
              </span>
              <span className="tg-cards muted">{g.has_wisehockey ? 'Real data, in the app' : `${g.cards} cards`}</span>
            </label>
          </li>
        ))}
      </ul>
    </details>
  )
}

function TeamMark({ name }) {
  const team = teamOf(name)
  return (
    <span className="tg-team" title={name}>
      {team.logo && <img src={team.logo} alt="" />}
      {team.short || name}
    </span>
  )
}
