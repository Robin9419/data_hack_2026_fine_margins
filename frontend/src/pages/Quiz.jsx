import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import BackLink from '../components/BackLink'
import CardUnlock from '../components/CardUnlock'

// Trivia round: pick where you watched the game, then answer three questions. Each correct
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
          points: data.progress.points - progress.points,
          progress: data.progress,
        })
        setQueued([
          ...(data.legends ?? []).map((card) => ({ card, result: 'legend' })),
          ...(data.collectors ?? []).map((card) => ({ card, result: 'collector' })),
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
        <p className="muted">
          Answer three questions about the games played so far to win their special cards. Where are you watching? (In this demo you tell us. A real
          app would check your ticket.)
        </p>
        <div className="venue-choices">
          <button type="button" className="choice venue-choice" disabled={busy} onClick={() => start('home')}>
            <span className="ch-av venue-icon">📺</span>
            <span className="ch-txt">
              <strong>At home</strong>
              <small>Watching on TV. Win the standard card of each player.</small>
            </span>
          </button>
          <button type="button" className="choice venue-choice stadium" disabled={busy} onClick={() => start('stadium')}>
            <span className="ch-av venue-icon">🏟</span>
            <span className="ch-txt">
              <strong>At the stadium</strong>
              <small>Win the exclusive Stadium edition of the card and more reward points.</small>
            </span>
          </button>
        </div>
        {error && <p className="error">{error}</p>}
      </section>
    )
  }

  if (questions.length === 0 && gamesPlayed === 0) {
    return (
      <section className="quiz">
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
      <section className="quiz">
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
    <section className="quiz q-card">
      <p className="eyebrow">
        <span className="badge">Quiz</span>
        Question {index + 1} of {questions.length} · {venue === 'stadium' ? '🏟 Stadium' : '📺 At home'}
      </p>
      <h1>{question.prompt}</h1>
      {question.match && <p className="quiz-match">{question.match}</p>}
      {hinted ? (
        <p className="quiz-clue">💡 {question.hint}</p>
      ) : (
        <button type="button" className="quiz-hint" disabled={Boolean(missed)} onClick={() => setHinted(true)}>
          💡 Need a hint?
        </button>
      )}
      <p className="muted small">
        {question.reward === 'upgrade'
          ? 'Correct answer upgrades your card to the Stadium edition.'
          : `Correct answer unlocks this player's ${venue === 'stadium' ? 'Stadium' : ''} card.`}
      </p>

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
        <>
          <p className="quiz-retry">Not quite. It was {missed.answer}.</p>
          {missed.explanation && <p className="quiz-explain">{missed.explanation}</p>}
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
          continueLabel={queued.length > 0 ? 'Continue' : last ? 'Finish' : 'Next question'}
        />
      )}
    </section>
  )
}
