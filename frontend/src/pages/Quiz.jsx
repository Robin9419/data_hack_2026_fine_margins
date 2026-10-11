import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import CardUnlock from '../components/CardUnlock'

// Trivia round: pick where you watched the game, then answer three questions. Each correct
// answer unlocks a card. Each question has three options and one attempt. At the stadium you win the foil
// edition of the card and more reward points.
export default function Quiz() {
  const navigate = useNavigate()
  const { progress, setProgress } = useAuth()
  const [venue, setVenue] = useState(null)
  const [questions, setQuestions] = useState(null)
  const [index, setIndex] = useState(0)
  const [missed, setMissed] = useState(null) // { chosen, answer } once the current question was answered wrong
  const [unlock, setUnlock] = useState(null) // { card, result, points, progress }
  const [won, setWon] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const start = async (chosen) => {
    setBusy(true)
    setError(null)
    try {
      const data = await api.quizStart(chosen)
      setVenue(chosen)
      setQuestions(data.questions)
      setIndex(0)
      setMissed(null)
      setWon(0)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const answer = async (question, option) => {
    if (busy) return
    setBusy(true)
    setError(null)
    try {
      const data = await api.quizAnswer(question.id, option.id)
      if (!data.correct) {
        setMissed({ chosen: option.id, answer: data.answer })
      } else {
        setUnlock({
          card: data.card,
          result: data.result,
          points: data.progress.points - progress.points,
          progress: data.progress,
        })
        setWon((n) => n + 1)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  // The bar fills when the unlock screen is dismissed, so the player sees it move.
  const next = () => {
    if (unlock) setProgress(unlock.progress)
    setUnlock(null)
    setMissed(null)
    setIndex((i) => i + 1)
  }

  if (!venue) {
    return (
      <section className="quiz">
        <h1>Trivia time</h1>
        <p className="muted">
          Answer three questions about the game to win cards. Where are you watching? (In this demo you tell us. A real
          app would check your ticket.)
        </p>
        <div className="venue-choices">
          <button type="button" className="venue-choice" disabled={busy} onClick={() => start('home')}>
            <span className="venue-icon">📺</span>
            <strong>At home</strong>
            <span>Watching on TV. Win the standard card of each player.</span>
          </button>
          <button type="button" className="venue-choice stadium" disabled={busy} onClick={() => start('stadium')}>
            <span className="venue-icon">🏟</span>
            <strong>At the stadium</strong>
            <span>Win the exclusive Stadium edition of the card and more reward points.</span>
          </button>
        </div>
        {error && <p className="error">{error}</p>}
        <Link to="/">← Back to collection</Link>
      </section>
    )
  }

  if (questions.length === 0) {
    return (
      <section className="quiz">
        <h1>Nothing left to win</h1>
        <p className="muted">
          {venue === 'stadium'
            ? 'You already own every card as a Stadium edition.'
            : 'You already own every card. Come to the stadium to win the Stadium editions!'}
        </p>
        <button type="button" className="pack-button" onClick={() => navigate('/')}>
          Back to collection
        </button>
      </section>
    )
  }

  const done = index >= questions.length
  if (done) {
    return (
      <section className="quiz">
        <h1>Round complete</h1>
        <p className="muted">
          You unlocked {won} {won === 1 ? 'card' : 'cards'}.
        </p>
        <div className="pack-actions">
          <button type="button" className="pack-button" onClick={() => navigate('/')}>
            Go to my collection
          </button>{' '}
          <button type="button" className="pack-button secondary" onClick={() => start(venue)} disabled={busy}>
            Another round
          </button>
        </div>
      </section>
    )
  }

  const question = questions[index]
  const last = index === questions.length - 1

  return (
    <section className="quiz">
      <p className="eyebrow">
        Question {index + 1} of {questions.length} · {venue === 'stadium' ? '🏟 Stadium' : '📺 At home'}
      </p>
      <h1>{question.prompt}</h1>
      <p className="quiz-match">{question.match}</p>
      <p className="quiz-clue">💡 {question.clue}</p>
      <p className="muted small">
        {question.reward === 'upgrade'
          ? 'Correct answer upgrades your card to the Stadium edition.'
          : `Correct answer unlocks this player's ${venue === 'stadium' ? 'Stadium' : ''} card.`}
      </p>

      <ul className="quiz-options">
        {question.options.map((option) => {
          const isWrong = missed?.chosen === option.id
          return (
            <li key={option.id}>
              <button
                type="button"
                className={`quiz-option ${isWrong ? 'wrong' : ''}`}
                disabled={Boolean(missed) || busy}
                onClick={() => answer(question, option)}
              >
                <strong>{option.name}</strong>
                <span>{option.team}</span>
              </button>
            </li>
          )
        })}
      </ul>
      {missed && (
        <>
          <p className="quiz-retry">Not quite. It was {missed.answer}.</p>
          <button type="button" className="pack-button" onClick={next}>
            {last ? 'Finish' : 'Next question'}
          </button>
        </>
      )}
      {error && <p className="error">{error}</p>}

      {unlock && (
        <CardUnlock
          card={unlock.card}
          result={unlock.result}
          points={unlock.points}
          onContinue={next}
          continueLabel={last ? 'Finish' : 'Next question'}
        />
      )}
    </section>
  )
}
