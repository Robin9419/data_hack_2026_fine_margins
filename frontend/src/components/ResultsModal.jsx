import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { formatMatchDate } from '../format'
import { useTournament } from '../tournament'
import TeamName from './TeamName'

const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`
const points = (w) => [w.goals && plural(w.goals, 'goal'), w.assists && plural(w.assists, 'assist')].filter(Boolean).join(', ')

// Pops up after a move along the timeline played games: the results, how each prediction went and the packs it
// earned, the Ones to Watch packs (an owned Road to Final card whose player scored or assisted), with a button that
// opens all waiting packs at once.
export default function ResultsModal() {
  const navigate = useNavigate()
  const { setProgress } = useAuth()
  const { tournament, justPlayed, dismissResults, refresh } = useTournament()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!justPlayed.length) return
    const onKey = (e) => e.key === 'Escape' && dismissResults()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [justPlayed, dismissResults])

  if (!justPlayed.length) return null

  const earned = justPlayed.reduce((n, g) => n + g.packs, 0)
  const watched = justPlayed.flatMap((g) => g.watch_packs ?? [])
  const waiting = tournament?.packs_waiting ?? earned + watched.reduce((n, w) => n + w.packs, 0)
  const predicted = justPlayed.some((g) => g.questions.some((q) => q.prediction))
  const days = [...new Set(justPlayed.filter((g) => g.kind !== 'outlook').map((g) => g.date))]

  const openPacks = async () => {
    setBusy(true)
    setError(null)
    try {
      const data = await api.openAllPacks()
      setProgress(data.progress)
      refresh()
      dismissResults()
      navigate('/pack', { state: { pack: data.pack, title: data.title } })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="results-overlay" onClick={dismissResults}>
      <div
        className="results-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="results-title"
        onClick={(e) => e.stopPropagation()}
      >
        <button type="button" className="results-close" aria-label="Close" onClick={dismissResults}>
          ✕
        </button>
        <p className="eyebrow">{days.map(formatMatchDate).join(', ')}</p>
        <h2 id="results-title">The results are in</h2>
        <p className="muted small">
          {!predicted
            ? 'You made no predictions for these games.'
            : earned
              ? `Your right picks earned ${plural(earned, 'pack')}.`
              : 'No right picks this time. Better luck on the next gameday!'}
          {watched.length > 0 && ` Your Ones to Watch earned ${plural(watched.length, 'bonus pack')}.`}
        </p>

        <div className="results-games">
          {justPlayed.map((g) => (
            <article key={g.id} className="results-game">
              {g.kind === 'outlook' ? (
                <strong className="predict-outlook-title">🏆 Your tournament predictions</strong>
              ) : (
                <div className="game-teams">
                  <TeamName name={g.home_team} />
                  <strong className="game-score">
                    {g.home_score}–{g.away_score}
                  </strong>
                  <TeamName name={g.away_team} right />
                </div>
              )}
              {g.questions.some((q) => q.prediction) ? (
                <ul className="results-picks">
                  {g.questions.map((q) => {
                    const pick = q.options.find((o) => o.id === q.prediction)
                    const answer = q.options.find((o) => o.id === q.answer)
                    const right = q.prediction === q.answer
                    return (
                      <li key={q.id}>
                        <span className={!pick ? 'skip' : right ? 'tick' : 'cross'}>{!pick ? '–' : right ? '✓' : '✗'}</span>
                        <span>
                          <strong>{q.prompt}</strong>
                          <small>
                            {pick ? `You: ${pick.label}` : 'No pick'}
                            {(!right || !pick) && ` · Answer: ${answer.label}`}
                          </small>
                          <small className="muted">{q.explanation}</small>
                        </span>
                      </li>
                    )
                  })}
                </ul>
              ) : (
                <p className="muted small">
                  {g.kind === 'outlook' ? 'You made no tournament predictions.' : 'No predictions for this game.'}
                </p>
              )}
              {g.packs > 0 && <p className="results-earned">+ {plural(g.packs, 'pack')}</p>}
              {g.watch_packs?.map((w) => (
                <p key={w.card_id} className="results-earned">
                  + {plural(w.packs, 'pack')} · Ones to Watch: {w.name} ({points(w)})
                </p>
              ))}
            </article>
          ))}
        </div>

        {error && <p className="error small">{error}</p>}
        <div className="results-actions">
          {waiting > 0 ? (
            <>
              <button type="button" className="pack-button" disabled={busy} onClick={openPacks}>
                Open {plural(waiting, 'pack')}
              </button>
              <button type="button" className="link-button" onClick={dismissResults}>
                Later
              </button>
            </>
          ) : (
            <button type="button" className="pack-button" onClick={dismissResults}>
              Continue
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
