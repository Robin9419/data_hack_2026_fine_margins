import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { TEAMS } from '../teams'


export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [mode, setMode] = useState('signup')
  const signingUp = mode === 'signup'
  const [username, setUsername] = useState('')
  const [favorite, setFavorite] = useState(null)
  // team name -> number of cards the set has for that club
  const [cardCounts, setCardCounts] = useState(null)
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    api
      .teams()
      .then((data) => setCardCounts(Object.fromEntries(data.teams.map((t) => [t.name, t.cards]))))
      .catch(() => {})
  }, [])

  const noCards = favorite && cardCounts && !cardCounts[favorite]

  const onSubmit = async (e) => {
    e.preventDefault()
    if (!username.trim()) return
    setSubmitting(true)
    setError(null)
    try {
      const data = await login(username.trim(), signingUp ? favorite : null)
      // Only a brand new account gets a starter pack.
      if (data.pack) navigate('/pack', { state: { pack: data.pack } })
      else navigate('/')
    } catch (err) {
      setError(err.message)
      setSubmitting(false)
    }
  }

  return (
    <>
      <div className="home-ghost" aria-hidden="true">
        <h1>Your Collection Highlights</h1>
        <div className="card-grid home-row">
          {[0, 1, 2, 3].map((i) => (
            <span key={i} className={`hero-card ${i % 2 ? 'team-usc' : 'team-hcd'}`}>?</span>
          ))}
        </div>
        <h2 className="home-subtitle">Latest Performances</h2>
        <div className="card-grid home-row">
          {[0, 1, 2, 3].map((i) => (
            <span key={i} className={`hero-card ${i % 2 ? 'team-hcd' : 'team-usc'}`}>?</span>
          ))}
        </div>
      </div>

      <div className="auth-overlay">
      <section className="signup q-card auth-modal" role="dialog" aria-modal="true" aria-labelledby="auth-title">
        <p className="hero-eyebrow">Spengler Cup · Davos · 26–31 December</p>
        <h1 className="auth-hero">
          Your Spengler Cup, one card at a time.
        </h1>
        <p className="muted auth-lead">
          The world’s oldest invitational hockey tournament, in your pocket. Collect the players and legends of every
          club, predict the games, test yourself with trivia and watch your collection grow with each day of the
          tournament.
        </p>
        <div className="auth-tabs" role="tablist">
          <button type="button" role="tab" aria-selected={signingUp} className={signingUp ? 'active' : ''} onClick={() => { setMode('signup'); setError(null) }}>Sign up</button>
          <button type="button" role="tab" aria-selected={!signingUp} className={!signingUp ? 'active' : ''} onClick={() => { setMode('login'); setError(null) }}>Log in</button>
        </div>
        <h2 id="auth-title" className="auth-title">{signingUp ? 'Start your collection' : 'Welcome back'}</h2>
        <form onSubmit={onSubmit} className="login-form">
          <label htmlFor="username">Username</label>
          <input
            id="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="e.g. puckfan"
            maxLength={40}
            autoFocus
          />

          {signingUp && <fieldset className="team-picker">
            <legend>
              Favorite team <span className="muted">(optional)</span>
            </legend>
            <div className="team-grid">
              {TEAMS.map((t) => (
                <button
                  type="button"
                  key={t.name}
                  className={`choice team-option ${favorite === t.name ? 'selected' : ''}`}
                  style={{ '--c1': t.c1, '--c2': t.c2 }}
                  aria-pressed={favorite === t.name}
                  onClick={() => setFavorite(favorite === t.name ? null : t.name)}
                >
                  <span className="ch-av">
                    <img src={t.logo} alt="" loading="lazy" />
                  </span>
                  <span className="team-name ch-txt">{t.name}</span>
                  <span className="ch-mark" aria-hidden="true" />
                </button>
              ))}
            </div>
            <p className="team-hint muted small">
              {!favorite && 'Pick a club and your free pack is guaranteed to include one of its players.'}
              {favorite && !noCards && `Your free pack will include at least one ${favorite} card.`}
              {noCards && `${favorite} has no cards from this match yet, so your pack will be a surprise.`}
            </p>
          </fieldset>}

          <button type="submit" className="cta" disabled={submitting || !username.trim()}>
            {submitting ? (signingUp ? 'Opening…' : 'Logging in…') : signingUp ? 'Open my free pack' : 'Log in'}
          </button>
          {error && <p className="error">{error}</p>}
        </form>
        <p className="muted small">
          Demo sign-in: no passwords and no real accounts. Log in with an existing name to pick up where you left off.
        </p>
      </section>
      </div>
    </>
  )
}
