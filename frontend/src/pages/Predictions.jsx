import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import TeamName, { TeamLogo } from '../components/TeamName'
import { formatMatchDate } from '../format'
import { useTournament } from '../tournament'

const dayName = (iso) => new Date(iso).toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })
const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`

// The gameday's predictions, one question at a time: pick an answer and the next question follows. A summary of the
// picks closes the round. Every right pick earns a pack once the games are played (the next stop on the timeline),
// and the results arrive in a pop-up.
export default function Predictions() {
  const { tournament } = useTournament()
  if (!tournament) return <p className="muted">Loading…</p>

  const { stage, today, timeline, results } = tournament
  const next = timeline[timeline.findIndex((s) => s.state === 'current') + 1]
  const open = today.filter((g) => !g.played && !g.locked)

  return (
    <section className="predict">
      <Link to="/" className="back-link">
        ← Back to collection
      </Link>
      {open.length > 0 ? (
        // Keyed by stage, so a new gameday starts at its first question.
        <Round key={stage} stage={stage} games={open} next={next} />
      ) : (
        <NoRound stage={stage} today={today} next={next} />
      )}
      <PastResults results={results} />
    </section>
  )
}

function Round({ stage, games, next }) {
  const navigate = useNavigate()
  const { predict, setStage, busy: stageBusy } = useTournament()
  const steps = games.flatMap((game) => game.questions.map((question) => ({ game, question })))
  const firstOpen = steps.findIndex((s) => !s.question.prediction)
  const [step, setStep] = useState(firstOpen === -1 ? null : firstOpen) // null: the summary
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const picked = steps.filter((s) => s.question.prediction).length

  const choose = async (game, question, option) => {
    if (busy) return
    setBusy(true)
    setError(null)
    try {
      await predict(game.id, question.id, option.id)
      // On to the next question still without a pick, or the summary once every question has one.
      const after = steps.findIndex((s, i) => i > step && !s.question.prediction)
      const before = steps.findIndex((s, i) => i < step && !s.question.prediction)
      setStep(after !== -1 ? after : before !== -1 ? before : null)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const current = step === null ? null : steps[step]

  return (
    <>
      <header className="predict-head">
        <p className="eyebrow">
          <span className="badge">Prediction</span>Gameday · {games[0].stage}
        </p>
        <h1>Your predictions</h1>
        <p className="muted">
          {dayName(stage)} · {plural(games.length, 'game')}. Every right pick earns a pack of three cards after the
          game.
        </p>
        <div className="predict-progress" aria-label={`${picked} of ${steps.length} picks made`}>
          <span style={{ width: `${(picked / steps.length) * 100}%` }} />
        </div>
        <p className="muted small">
          {picked} of {steps.length} picks
        </p>
      </header>

      {current ? (
        <article className="predict-card q-card">
          <div className="predict-game">
            <span className="muted small">
              Game {games.indexOf(current.game) + 1} of {games.length} · {current.game.start}
            </span>
            <div className="game-teams">
              <TeamName name={current.game.home_team} />
              <strong className="game-score">vs</strong>
              <TeamName name={current.game.away_team} right />
            </div>
          </div>
          <p className="predict-count">
            Question {current.game.questions.indexOf(current.question) + 1} of {current.game.questions.length}
          </p>
          <h2 className="predict-prompt">{current.question.prompt}</h2>
          <p className="muted small">{current.question.hint}</p>
          <div className="predict-options">
            {current.question.options.map((o) => (
              <button
                key={o.id}
                type="button"
                className={`choice predict-option ${current.question.prediction === o.id ? 'selected' : ''}`}
                aria-pressed={current.question.prediction === o.id}
                disabled={busy}
                onClick={() => choose(current.game, current.question, o)}
              >
                {o.team && (
                  <span className="ch-av">
                    <TeamLogo name={o.team} />
                  </span>
                )}
                <span className="ch-txt">{o.label}</span>
                <span className="ch-mark" aria-hidden="true" />
              </button>
            ))}
          </div>
          {error && <p className="error small">{error}</p>}
          <nav className="predict-nav">
            <button type="button" className="link-button" disabled={step === 0} onClick={() => setStep(step - 1)}>
              ← Previous
            </button>
            <button type="button" className="link-button" onClick={() => setStep(null)}>
              See all picks
            </button>
            <button
              type="button"
              className="link-button"
              onClick={() => setStep(step + 1 < steps.length ? step + 1 : null)}
            >
              {current.question.prediction ? 'Next →' : 'Skip →'}
            </button>
          </nav>
        </article>
      ) : (
        <article className="predict-card q-card">
          <h2 className="predict-prompt">{picked === steps.length ? 'All set!' : `${steps.length - picked} picks left`}</h2>
          <p className="muted small">
            {picked === steps.length
              ? `Up to ${plural(picked, 'pack')} to win. The results come once the games are played.`
              : 'Tap a question to make your pick. Every pick is a chance at a pack.'}
          </p>
          {games.map((game) => (
            <div key={game.id} className="predict-summary">
              <div className="game-teams">
                <TeamName name={game.home_team} />
                <strong className="game-score">vs</strong>
                <TeamName name={game.away_team} right />
              </div>
              <ul>
                {game.questions.map((q) => {
                  const option = q.options.find((o) => o.id === q.prediction)
                  return (
                    <li key={q.id}>
                      <button
                        type="button"
                        className="predict-summary-row"
                        onClick={() => setStep(steps.findIndex((s) => s.question === q))}
                      >
                        <span>{q.prompt}</span>
                        <strong className={option ? '' : 'muted'}>
                          {option ? option.label : 'Make a pick'} <span aria-hidden="true">›</span>
                        </strong>
                      </button>
                    </li>
                  )
                })}
              </ul>
            </div>
          ))}
          <div className="predict-actions">
            <button type="button" className="pack-button" onClick={() => navigate('/')}>
              Done
            </button>
            {next && (
              <button type="button" className="pack-button secondary-light" disabled={stageBusy} onClick={() => setStage(next.id)}>
                Play today's games →
              </button>
            )}
          </div>
        </article>
      )}
    </>
  )
}

function NoRound({ stage, today, next }) {
  const { setStage, busy } = useTournament()
  return (
    <header className="predict-head">
      <p className="eyebrow">Predictions</p>
      {stage === 'pre' ? (
        <>
          <h1>Predictions open on Friday 26 December</h1>
          <p className="muted">
            On every gameday you predict the winner, a goal question and one stat of each game. Every right pick
            earns a pack after the game.
          </p>
        </>
      ) : stage === 'post' ? (
        <>
          <h1>The tournament is over</h1>
          <p className="muted">There is nothing left to predict. See how your predictions went below.</p>
        </>
      ) : (
        <>
          <h1>{dayName(stage)}</h1>
          <p className="muted">
            {today.length
              ? 'You already played these games further along the timeline, so their predictions are locked.'
              : 'No games today.'}
          </p>
        </>
      )}
      {next && (
        <button type="button" className="pack-button predict-next" disabled={busy} onClick={() => setStage(next.id)}>
          {stage === 'pre' ? 'Go to the first gameday →' : next.id === 'post' ? 'Play the final →' : `Go to ${next.label} Dec →`}
        </button>
      )}
    </header>
  )
}

function PastResults({ results }) {
  const predicted = results.filter((g) => g.questions.some((q) => q.prediction))
  if (!predicted.length) return null
  return (
    <details className="predict-past">
      <summary>Your past predictions ({predicted.length})</summary>
      <ul>
        {predicted.map((g) => (
          <li key={g.id}>
            <span className="muted small">{formatMatchDate(g.date)}</span>
            <span>
              {g.home_team} {g.home_score}–{g.away_score} {g.away_team}
            </span>
            <strong>
              {g.correct} of {g.questions.filter((q) => q.prediction).length} right
            </strong>
          </li>
        ))}
      </ul>
    </details>
  )
}
