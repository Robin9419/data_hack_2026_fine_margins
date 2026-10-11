import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import CardTile from '../components/CardTile'

export default function Gallery() {
  const location = useLocation()
  const navigate = useNavigate()
  const { setProgress } = useAuth()
  const newCardIds = location.state?.newCardIds ?? []
  const [cards, setCards] = useState(null)
  const [error, setError] = useState(null)

  const load = () =>
    api
      .cards()
      .then((data) => {
        setCards(data.cards)
        setProgress(data.progress)
      })
      .catch((err) => setError(err.message))

  useEffect(() => {
    load()
  }, [])

  const onReset = async () => {
    const data = await api.reset()
    setProgress(data.progress)
    navigate('/pack', { state: { pack: data.pack } })
  }

  if (error) return <p className="error">{error}</p>
  if (!cards) return <p className="muted">Loading cards…</p>

  const ownedCount = cards.filter((c) => c.owned).length

  return (
    <section>
      {newCardIds.length > 0 && (
        <div className="banner">
          {newCardIds.length} new {newCardIds.length === 1 ? 'card' : 'cards'} added to your collection. Tap a card to
          see its stats.
        </div>
      )}

      <div className="gallery-header">
        <h1>Your collection</h1>
        <span className="progress">
          {ownedCount} / {cards.length} collected
        </span>
      </div>

      <Link to="/quiz" className="quiz-cta">
        <span>
          <strong>Play trivia, win more cards</strong>
          <small>Three questions about the game. Answer at the stadium for the exclusive Stadium edition.</small>
        </span>
        <span aria-hidden="true">→</span>
      </Link>

      <div className="card-grid">
        {cards.map((card) => (
          <CardTile key={card.id} card={card} isNew={newCardIds.includes(card.id)} />
        ))}
      </div>

      <button className="link-button reset" onClick={onReset}>
        Reset collection and start over with a new starter pack
      </button>
    </section>
  )
}
