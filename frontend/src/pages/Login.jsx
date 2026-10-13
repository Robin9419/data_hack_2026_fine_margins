import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'

const TEAMS = [
  { name: 'SCL Tigers', short: 'SCL', logo: '/logos/scl.png', c1: '#111111', c2: '#f58220' },
  { name: 'Adler Mannheim', short: 'ADL', logo: '/logos/adler.png', c1: '#0b2a5b', c2: '#d6001c' },
  { name: 'Ilves Tampere', short: 'ILV', logo: '/logos/ilves.png', c1: '#111111', c2: '#f5c400' },
  { name: 'HC Davos', short: 'HCD', logo: '/logos/davos.png', c1: '#0a2d6e', c2: '#ffd400' },
  { name: 'Frölunda HC', short: 'FHC', logo: '/logos/frolunda.png', c1: '#00573f', c2: '#ffffff' },
  { name: 'U.S. Collegiate Selects', short: 'USA', logo: '/logos/usa.png', c1: '#13284f', c2: '#ff4d5a' },
]

const STEPS = [
  { icon: '🎁', title: 'Open your starter pack', text: 'Three free cards, each one a player’s performance in the match.' },
  { icon: '🧠', title: 'Answer the trivia', text: 'Work out who made the difference from the clues and win more cards.' },
  { icon: '🏆', title: 'Collect and unlock', text: 'Watch the highlights and earn points towards rewards.' },
]

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
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
      const data = await login(username.trim(), favorite)
      // Only a brand new account gets a starter pack.
      if (data.pack) navigate('/pack', { state: { pack: data.pack } })
      else navigate('/')
    } catch (err) {
      setError(err.message)
      setSubmitting(false)
    }
  }

  return (
    <div className="landing">
      <section className="hero">
        <div className="hero-glow" aria-hidden="true" />
        <p className="hero-eyebrow">Spengler Cup</p>
        <h1>
          The match is over.
          <br />
          Who made the difference?
        </h1>
        <p className="hero-lead">
          Turn the performances that defined the game into collectible cards. Every card is backed by real match data,
          with the highlight to prove it.
        </p>
        <div className="hero-cards" aria-hidden="true">
          <span className="hero-card hc-1 team-hcd">?</span>
          <span className="hero-card hc-2 team-usc">?</span>
          <span className="hero-card hc-3 team-hcd">?</span>
        </div>
      </section>

      <section className="signup">
        <h2>Start your collection</h2>
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

          <fieldset className="team-picker">
            <legend>
              Favorite team <span className="muted">(optional)</span>
            </legend>
            <div className="team-grid">
              {TEAMS.map((t) => (
                <button
                  type="button"
                  key={t.name}
                  className={`team-option ${favorite === t.name ? 'selected' : ''}`}
                  style={{ '--c1': t.c1, '--c2': t.c2 }}
                  aria-pressed={favorite === t.name}
                  onClick={() => setFavorite(favorite === t.name ? null : t.name)}
                >
                  <span className="team-badge">
                    <img src={t.logo} alt="" loading="lazy" />
                  </span>
                  <span className="team-name">{t.name}</span>
                </button>
              ))}
            </div>
            <p className="team-hint muted small">
              {!favorite && 'Pick a club and your free pack is guaranteed to include one of its players.'}
              {favorite && !noCards && `Your free pack will include at least one ${favorite} card.`}
              {noCards && `${favorite} has no cards from this match yet, so your pack will be a surprise.`}
            </p>
          </fieldset>

          <button type="submit" className="cta" disabled={submitting || !username.trim()}>
            {submitting ? 'Opening…' : 'Get my free cards'}
          </button>
          {error && <p className="error">{error}</p>}
        </form>
        <p className="muted small">
          Demo sign-in: no passwords and no real accounts. Use an existing name to pick up where you left off.
        </p>
      </section>

      <section className="steps">
        {STEPS.map((s, i) => (
          <div className="step" key={s.title}>
            <span className="step-icon">{s.icon}</span>
            <h3>
              {i + 1}. {s.title}
            </h3>
            <p className="muted">{s.text}</p>
          </div>
        ))}
      </section>
    </div>
  )
}
