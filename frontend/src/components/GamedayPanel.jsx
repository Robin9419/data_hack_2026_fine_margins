import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { formatMatchDate } from '../format'
import { teamOf } from '../teams'
import { useTournament } from '../tournament'

const dayName = (iso) => new Date(iso).toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })
const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`

// The gallery's view of the tournament timeline: what is going on before, during and after the 2025 Spengler Cup.
// On a gameday the user predicts three things per game; the results and the packs they earn come once the games
// are played (the next stop on the timeline).
export default function GamedayPanel() {
  const { tournament, setStage, busy } = useTournament()
  if (!tournament) return null

  const { stage, today, results, timeline, champion } = tournament
  const next = timeline[timeline.findIndex((s) => s.state === 'current') + 1]
  const lastDay = results[0]?.date
  const latest = results.filter((g) => g.date === lastDay)
  const waiting = results.filter((g) => g.date !== lastDay && g.packs > 0 && !g.packs_claimed)
  const earlier = results.filter((g) => g.date !== lastDay && !waiting.includes(g))

  return (
    <section className="gameday" aria-label="Tournament">
      {stage === 'pre' && (
        <div className="gameday-intro">
          <p className="eyebrow">Before the tournament</p>
          <h2>The Spengler Cup starts on Friday 26 December</h2>
          <p className="muted">
            Until the first puck drops the set holds base cards and club legends only. The special cards of a game, the
            Road to Final cards and the trivia arrive once the game is played. On every gameday you can predict the
            winner, the first goal and one stat of each game: every right call earns a pack after the game.
          </p>
        </div>
      )}

      {today.length > 0 && (
        <>
          <div className="gameday-intro">
            <p className="eyebrow">Gameday · {today[0].stage}</p>
            <h2>{dayName(stage)}</h2>
            <p className="muted">
              Make your predictions before the games. Every right one earns a pack once the game is over: move on to
              the next day in the timeline to play the games.
            </p>
          </div>
          <div className="gameday-games">
            {today.map((g) => (
              <GameCard key={g.id} game={g} />
            ))}
          </div>
        </>
      )}

      {stage === 'post' && champion && (
        <div className="gameday-intro">
          <p className="eyebrow">After the tournament</p>
          <h2>
            <TeamLogo name={champion} /> {champion} win the Spengler Cup
          </h2>
          <p className="muted">Every card of the tournament is out now, including the final's Wisehockey cards.</p>
        </div>
      )}

      {latest.length > 0 && (
        <>
          <h3 className="gameday-heading">Results · {formatMatchDate(lastDay)}</h3>
          <div className="gameday-games">
            {latest.map((g) => (
              <GameCard key={g.id} game={g} />
            ))}
          </div>
        </>
      )}

      {waiting.length > 0 && (
        <>
          <h3 className="gameday-heading">Packs still to open</h3>
          <div className="gameday-games">
            {waiting.map((g) => (
              <GameCard key={g.id} game={g} />
            ))}
          </div>
        </>
      )}

      {earlier.length > 0 && (
        <details className="gameday-earlier">
          <summary>Earlier results ({earlier.length})</summary>
          <div className="gameday-games">
            {earlier.map((g) => (
              <GameCard key={g.id} game={g} />
            ))}
          </div>
        </details>
      )}

      {next && (
        <button type="button" className="pack-button gameday-next" disabled={busy} onClick={() => setStage(next.id)}>
          {stage === 'pre'
            ? `Go to the first gameday (${next.label} Dec) →`
            : next.id === 'post'
              ? 'Play the final →'
              : `Play today's games, go to ${next.label} Dec →`}
        </button>
      )}
    </section>
  )
}

function GameCard({ game }) {
  const navigate = useNavigate()
  const { setProgress } = useAuth()
  const { predict, refresh } = useTournament()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const open = !game.played && !game.locked
  const predicted = game.questions.filter((q) => q.prediction).length

  const choose = async (question, option) => {
    if (!open || busy) return
    setBusy(true)
    setError(null)
    try {
      await predict(game.id, question.id, option.id)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const openPacks = async () => {
    setBusy(true)
    setError(null)
    try {
      const data = await api.openGamePacks(game.id)
      setProgress(data.progress)
      refresh()
      navigate('/pack', { state: { pack: data.pack, title: data.title } })
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <article className={`game-card ${game.played ? 'played' : ''}`}>
      <header className="game-head">
        <span className="muted small">
          {game.stage} · {game.start}
        </span>
        <div className="game-teams">
          <TeamName name={game.home_team} />
          <strong className="game-score">{game.played ? `${game.home_score}–${game.away_score}` : 'vs'}</strong>
          <TeamName name={game.away_team} right />
        </div>
      </header>

      <ol className="predictions">
        {game.questions.map((q) => {
          const right = game.played && q.prediction === q.answer
          return (
            <li key={q.id} className="prediction">
              <p className="prediction-prompt">
                {game.played && q.prediction && <span className={right ? 'tick' : 'cross'}>{right ? '✓' : '✗'}</span>}
                {q.prompt}
              </p>
              {open && <p className="muted small">{q.hint}</p>}
              <div className="prediction-options">
                {q.options.map((o) => {
                  const classes = ['filter-chip', 'prediction-option']
                  if (q.prediction === o.id) classes.push('active')
                  if (game.played && o.id === q.answer) classes.push('answer')
                  if (game.played && q.prediction === o.id && !right) classes.push('wrong')
                  return (
                    <button
                      key={o.id}
                      type="button"
                      className={classes.join(' ')}
                      disabled={!open || busy}
                      aria-pressed={q.prediction === o.id}
                      onClick={() => choose(q, o)}
                    >
                      {o.team && <TeamLogo name={o.team} />}
                      {o.label}
                    </button>
                  )
                })}
              </div>
              {game.played && <p className="muted small prediction-result">{q.explanation}</p>}
            </li>
          )
        })}
      </ol>

      <footer className="game-foot">
        {open && (
          <span className="muted small">
            {predicted === 0
              ? `${game.questions.length} predictions, up to ${plural(game.questions.length, 'pack')} after the game`
              : `${predicted} of ${game.questions.length} predicted · up to ${plural(predicted, 'pack')} after the game`}
          </span>
        )}
        {!game.played && game.locked && (
          <span className="muted small">You already played this game further along the timeline.</span>
        )}
        {game.played &&
          (predicted === 0 ? (
            <span className="muted small">No predictions for this game.</span>
          ) : game.packs === 0 ? (
            <span className="muted small">0 of {predicted} right, no pack this time.</span>
          ) : game.packs_claimed ? (
            <span className="muted small">
              {game.correct} right · {plural(game.packs, 'pack')} opened
            </span>
          ) : (
            <button type="button" className="pack-button" disabled={busy} onClick={openPacks}>
              {game.correct} right · Open {plural(game.packs, 'pack')}
            </button>
          ))}
        {error && <p className="error small">{error}</p>}
      </footer>
    </article>
  )
}

function TeamLogo({ name }) {
  const team = teamOf(name)
  return team.logo ? <img className="team-logo" src={team.logo} alt="" /> : null
}

function TeamName({ name, right }) {
  return (
    <span className={`game-team ${right ? 'right' : ''}`}>
      <TeamLogo name={name} />
      <span>{name}</span>
    </span>
  )
}
