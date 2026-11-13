import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import BackLink from '../components/BackLink'
import CardUnlock from '../components/CardUnlock'

// Trivia round: pick where you watched the game, then answer five questions. One round per gameday. Each correct
// answer unlocks a card. Each question has three options and one attempt. At the stadium you win the foil
// edition of the card and more reward points.
export default function Quiz() {
  const navigate = useNavigate()
  const { progress, setProgress } = useAuth()
  const [venue, setVenue] = useState(null)
  const [questions, setQuestions] = useState(null)
  const [gamesPlayed, setGamesPlayed] = useState(0)
  const [index, setIndex] = useState(0)
  const [missed, setMissed] = useState(null) // { chosen, answerId, answer, explanation } once answered wrong
  const [hinted, setHinted] = useState(false) // the hint of the current question is shown
  const [unlock, setUnlock] = useState(null) // { card, result, points, progress }
  const [queued, setQueued] = useState([]) // { card, result } of the legends and collectors earned by the last answer, shown after its unlock
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
      setGamesPlayed(data.games_played)
      setIndex(0)
      setMissed(null)
      setHinted(false)
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
        setMissed({ chosen: option.id, answerId: data.answer_id, answer: data.answer, explanation: data.explanation })
      } else {
        setUnlock({
          card: data.card,
          result: data.result,
          points: data.points,
          progress: data.progress,
        })
        setQueued([
          ...(data.legends ?? []).map((card) => ({ card, result: 'legend' })),
          ...(data.collectors ?? []).map((card) => ({ card, result: card.kind === 'collector' ? 'collector' : 'context' })),
        ])
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
    if (queued.length > 0) {
      const [{ card, result }, ...rest] = queued
      setUnlock({ ...unlock, card, result, points: null })
      setQueued(rest)
      return
    }
    if (unlock) setProgress(unlock.progress)
    setUnlock(null)
    setMissed(null)
    setHinted(false)
    setIndex((i) => i + 1)
  }

  if (!venue) {
    return (
      <section className="quiz q-card">
        <BackLink />
        <p className="eyebrow"><span className="badge">Quiz</span></p>
        <h1>Trivia time</h1>
        <p className="quiz-lede">Answer five questions about the games so far. Every right answer wins a special card. One round per gameday.</p>
        <h2 className="quiz-subhead">Where are you watching?</h2>
        <div className="venue-choices">
          <button type="button" className="choice venue-choice" disabled={busy} onClick={() => start('home')}>
            <span className="ch-av venue-icon">📺</span>
            <span className="ch-txt">
              <strong>At home</strong>
              <small>Win the standard card of each player.</small>
            </span>
          </button>
          <button type="button" className="choice venue-choice stadium" disabled={busy} onClick={() => start('stadium')}>
            <span className="ch-av venue-icon">🏟</span>
            <span className="ch-txt">
              <strong>At the stadium</strong>
              <small>Win the exclusive Stadium edition and more reward points.</small>
            </span>
          </button>
        </div>
        <p className="quiz-footnote">Demo: you choose your venue here. The real app would check your ticket.</p>
        {error && <p className="error">{error}</p>}
      </section>
    )
  }

  if (questions.length === 0 && gamesPlayed === 0) {
    return (
      <section className="quiz q-card">
        <BackLink />
        <h1>No games played yet</h1>
        <p className="muted">
          The trivia asks about the games of the tournament, so it opens after the first one. Make your predictions on
          a gameday, then move on in the timeline at the bottom to play the games.
        </p>
      </section>
    )
  }

  if (questions.length === 0) {
    return (
      <section className="quiz q-card">
        <BackLink />
        <h1>Nothing left to win</h1>
        <p className="muted">
          {venue === 'stadium'
            ? 'You already own every special card of the games so far as a Stadium edition.'
            : 'You already own every special card of the games so far. Come to the stadium to win the Stadium editions, or play the next games!'}
        </p>
      </section>
    )
  }

  const done = index >= questions.length
  if (done) {
    return (
      <section className="quiz q-card">
        <h1>Round complete</h1>
        <p className="muted">
          You unlocked {won} {won === 1 ? 'card' : 'cards'}.
        </p>
        <p className="muted small">One round per gameday. The next one opens when you move on in the timeline.</p>
        <div className="pack-actions">
          <button type="button" className="pack-button" onClick={() => navigate('/collection')}>
            Go to my collection
          </button>
        </div>
      </section>
    )
  }

  const question = questions[index]
  const last = index === questions.length - 1

  return (
    <section className="quiz q-card">
      <div className="quiz-meta">
        <p className="eyebrow">
          <span className="badge">Quiz</span>
          {venue === 'stadium' ? '🏟 Stadium' : '📺 At home'}
        </p>
        <div className="quiz-steps" aria-label={`Question ${index + 1} of ${questions.length}`}>
          {questions.map((q, i) => (
            <span key={q.id} className={i < index ? 'done' : i === index ? 'current' : ''} />
          ))}
          <span className="quiz-steps-label">
            {index + 1} / {questions.length}
          </span>
        </div>
      </div>

      <div className="quiz-question">
        {question.match && <p className="quiz-match">{question.match}</p>}
        <h1>{question.prompt}</h1>
      </div>

      <div className="quiz-aids">
        <span className="quiz-reward">
          🎁{' '}
          {question.reward === 'upgrade'
            ? 'Upgrades your card to the Stadium edition'
            : `Unlocks this player's ${venue === 'stadium' ? 'Stadium ' : ''}card`}
        </span>
        {!hinted && (
          <button type="button" className="quiz-hint" disabled={Boolean(missed)} onClick={() => setHinted(true)}>
            💡 Need a hint?
          </button>
        )}
      </div>
      {hinted && <p className="quiz-clue">💡 {question.hint}</p>}

      <ul className="quiz-options">
        {question.options.map((option) => {
          const isWrong = missed?.chosen === option.id
          const isRight = missed?.answerId === option.id
          const ruledOut = hinted && option.id === question.eliminate && !isWrong
          const state = isWrong ? 'wrong' : isRight ? 'right' : ruledOut ? 'ruled-out' : ''
          return (
            <li key={option.id}>
              <button
                type="button"
                className={`choice quiz-option ${state} ${missed && !isWrong && !isRight ? 'dim' : ''}`}
                disabled={Boolean(missed) || busy || ruledOut}
                onClick={() => answer(question, option)}
              >
                <span className="ch-txt">
                  <strong>{option.name}</strong>
                  <small>{option.team}</small>
                </span>
                <span className="ch-mark" aria-hidden="true" />
              </button>
            </li>
          )
        })}
      </ul>
      {missed && (
        <div className="quiz-feedback">
          <p className="quiz-retry">Not quite. It was {missed.answer}.</p>
          {missed.explanation && <p className="quiz-explain">{missed.explanation}</p>}
          <button type="button" className="pack-button" onClick={next}>
            {last ? 'Finish' : 'Next question'}
          </button>
        </div>
      )}
      {error && <p className="error">{error}</p>}

      {unlock && (
        <CardUnlock
          card={unlock.card}
          result={unlock.result}
          points={unlock.points}
          onContinue={next}
          continueLabel={queued.length > 0 ? 'Continue' : last ? 'Finish' : 'Next question'}
        />
      )}
    </section>
  )
}
