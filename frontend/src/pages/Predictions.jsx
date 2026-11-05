import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import BackLink from '../components/BackLink'
import TeamName, { TeamLogo } from '../components/TeamName'
import { formatMatchDate } from '../format'
import { useTournament } from '../tournament'

const dayName = (iso) => new Date(iso).toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })
const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`

// The gameday's predictions, one question at a time: pick an answer and the next question follows. A summary of the
// picks closes the round. Every right pick earns a pack once the games are played (the next stop on the timeline),
// and the results arrive in a pop-up. Before the tournament the round is the tournament predictions (kind
// 'outlook'): they close on the first gameday and pay out after the final.
const isOutlook = (g) => g.kind === 'outlook'

// The teams of a game, or the title of the tournament predictions.
function RoundTeams({ game, score }) {
  if (isOutlook(game)) return <strong className="predict-outlook-title">🏆 Spengler Cup 2025</strong>
  return (
    <div className="game-teams">
      <TeamName name={game.home_team} />
      <strong className="game-score">{score ?? 'vs'}</strong>
      <TeamName name={game.away_team} right />
    </div>
  )
}
export default function Predictions() {
  const { tournament } = useTournament()
  if (!tournament) return <p className="muted">Loading…</p>

  const { stage, today, timeline, results } = tournament
  const next = timeline[timeline.findIndex((s) => s.state === 'current') + 1]
  const open = today.filter((g) => !g.played && !g.locked)

  return (
    <section className="predict">
      <BackLink />
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
  const outlook = games.some(isOutlook)

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
          <span className="badge">Prediction</span>
          {outlook ? 'Before the tournament' : `${dayName(stage)} · ${plural(games.length, 'game')}`}
        </p>
        <h1>{outlook ? 'Predict the tournament' : 'Your predictions'}</h1>
        <p className="predict-lede">
          {outlook
            ? 'Five calls on the whole Spengler Cup. Every right pick earns a pack after the final.'
            : 'Every right pick earns a pack once the game is played.'}
        </p>
        {outlook && <p className="predict-note">🔒 Picks lock when the first game starts.</p>}
        <div className="predict-meter">
          <div className="predict-progress" aria-hidden="true">
            <span style={{ width: `${(picked / steps.length) * 100}%` }} />
          </div>
          <span className="predict-meter-label">
            <strong>{picked}</strong> / {steps.length} picks
          </span>
        </div>
      </header>

      {current ? (
        <article className="predict-card q-card">
          <div className="predict-game">
            <span className="predict-game-label">
              {isOutlook(current.game)
                ? 'Tournament · 26 to 31 December'
                : `Game ${games.indexOf(current.game) + 1} of ${games.length} · ${current.game.start}`}
            </span>
            <RoundTeams game={current.game} />
          </div>
          <div className="predict-question">
            <p className="predict-count">
              Question {current.game.questions.indexOf(current.question) + 1} of {current.game.questions.length}
            </p>
            <h2 className="predict-prompt">{current.question.prompt}</h2>
            {current.question.hint && <p className="predict-hint">{current.question.hint}</p>}
          </div>
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
              <span className="chev prev" aria-hidden="true" /> Previous
            </button>
            <button type="button" className="link-button" onClick={() => setStep(null)}>
              See all picks
            </button>
            <button
              type="button"
              className="link-button"
              onClick={() => setStep(step + 1 < steps.length ? step + 1 : null)}
            >
              {current.question.prediction ? 'Next' : 'Skip'} <span className="chev next" aria-hidden="true" />
            </button>
          </nav>
        </article>
      ) : (
        <article className="predict-card q-card">
          <div className="predict-question">
            <h2 className="predict-prompt">{picked === steps.length ? 'All set!' : `${steps.length - picked} picks left`}</h2>
            <p className="predict-hint">
              {picked === steps.length
                ? `Up to ${plural(picked, 'pack')} to win. Results arrive once ${outlook ? 'the final is' : 'the games are'} played.`
                : 'Tap a question to make or change your pick.'}
            </p>
          </div>
          {games.map((game) => (
            <div key={game.id} className="predict-summary">
              <RoundTeams game={game} />
              <ul>
                {game.questions.map((q) => {
                  const option = q.options.find((o) => o.id === q.prediction)
                  return (
                    <li key={q.id}>
                      <button
                        type="button"
                        className={`predict-summary-row ${option ? '' : 'open'}`}
                        onClick={() => setStep(steps.findIndex((s) => s.question === q))}
                      >
                        <span className="predict-summary-q">{q.prompt}</span>
                        <span className="predict-summary-a">
                          {option ? option.label : 'Make a pick'}
                          <span className="chev next" aria-hidden="true" />
                        </span>
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
                {outlook ? 'Start the tournament →' : "Play today's games →"}
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
    <header className="predict-head q-card">
      <p className="eyebrow">
        <span className="badge">Prediction</span>
      </p>
      {stage === 'pre' ? (
        <>
          <h1>Game predictions open on Friday 26 December</h1>
          <p className="predict-lede">
            Your tournament predictions are locked in. On every gameday you predict the winner, a goal question and
            one stat of each game. Every right pick earns a pack after the game.
          </p>
        </>
      ) : stage === 'post' ? (
        <>
          <h1>The tournament is over</h1>
          <p className="predict-lede">There is nothing left to predict. See how your predictions went below.</p>
        </>
      ) : (
        <>
          <h1>{dayName(stage)}</h1>
          <p className="predict-lede">
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
  const [openId, setOpenId] = useState(null)
  const predicted = results.filter((g) => g.questions.some((q) => q.prediction))
  if (!predicted.length) return null
  return (
    <details className="predict-past q-card">
      <summary>
        <span>Your past predictions</span>
        <span className="predict-past-count">{predicted.length}</span>
        <span className="chev next" aria-hidden="true" />
      </summary>
      <ul>
        {predicted.map((g) => {
          const isOpen = openId === g.id
          const made = g.questions.filter((q) => q.prediction).length
          return (
            <li key={g.id} className={`predict-past-item ${isOpen ? 'open' : ''}`}>
              <button
                type="button"
                className="predict-past-toggle"
                aria-expanded={isOpen}
                onClick={() => setOpenId(isOpen ? null : g.id)}
              >
                <span className="predict-past-game">
                  <span className="predict-past-date">{isOutlook(g) ? 'Before the tournament' : formatMatchDate(g.date)}</span>
                  <span className="predict-past-title">
                    {isOutlook(g) ? 'Tournament predictions' : `${g.home_team} ${g.home_score}–${g.away_score} ${g.away_team}`}
                  </span>
                </span>
                <span className={`predict-past-score ${g.correct > 0 ? 'hit' : ''}`}>
                  {g.correct} / {made} right
                </span>
                <span className="chev next" aria-hidden="true" />
              </button>
              {isOpen && (
                <ul className="predict-past-questions">
                  {g.questions.map((q) => {
                    const pick = q.options.find((o) => o.id === q.prediction)
                    const answer = q.options.find((o) => o.id === q.answer)
                    const right = q.prediction && q.prediction === q.answer
                    const state = right ? 'right' : q.prediction ? 'wrong' : 'missed'
                    return (
                      <li key={q.id} className={state}>
                        <span className="predict-past-prompt">
                          <span className="predict-past-mark" aria-hidden="true">
                            {right ? '✓' : q.prediction ? '✕' : '–'}
                          </span>
                          {q.prompt}
                        </span>
                        <dl className="predict-past-answers">
                          <div>
                            <dt>Your pick</dt>
                            <dd>{pick ? pick.label : 'No pick'}</dd>
                          </div>
                          <div>
                            <dt>Answer</dt>
                            <dd>{answer ? answer.label : '—'}</dd>
                          </div>
                        </dl>
                        {q.explanation && <p className="predict-past-explain">{q.explanation}</p>}
                      </li>
                    )
                  })}
                </ul>
              )}
            </li>
          )
        })}
      </ul>
    </details>
  )
}
