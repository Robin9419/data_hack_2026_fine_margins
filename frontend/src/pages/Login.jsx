import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const onSubmit = async (e) => {
    e.preventDefault()
    if (!username.trim()) return
    setSubmitting(true)
    setError(null)
    try {
      const data = await login(username.trim())
      navigate('/', { state: { starterCardIds: data.starter_card_ids } })
    } catch (err) {
      setError(err.message)
      setSubmitting(false)
    }
  }

  return (
    <section className="login">
      <h1>The match is over. Who made the difference?</h1>
      <p className="muted">
        Collect the performances that defined the game. Sign in with any name to get three free starter cards.
      </p>
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
        <button type="submit" disabled={submitting || !username.trim()}>
          {submitting ? 'Signing in…' : 'Enter'}
        </button>
        {error && <p className="error">{error}</p>}
      </form>
      <p className="muted small">Demo sign-in: there are no passwords and no real accounts.</p>
    </section>
  )
}
