import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { api } from '../api'
import CardTile from '../components/CardTile'

export default function Gallery() {
  const location = useLocation()
  const starterCardIds = location.state?.starterCardIds ?? []
  const [cards, setCards] = useState(null)
  const [error, setError] = useState(null)

  const load = () =>
    api
      .cards()
      .then((data) => setCards(data.cards))
      .catch((err) => setError(err.message))

  useEffect(() => {
    load()
  }, [])

  const onReset = async () => {
    await api.reset()
    load()
  }

  if (error) return <p className="error">{error}</p>
  if (!cards) return <p className="muted">Loading cards…</p>

  const ownedCount = cards.filter((c) => c.owned).length

  return (
    <section>
      {starterCardIds.length > 0 && (
        <div className="banner">
          Welcome! You received {starterCardIds.length} free starter cards. Tap a card to see its stats.
        </div>
      )}

      <div className="gallery-header">
        <h1>Your collection</h1>
        <span className="progress">
          {ownedCount} / {cards.length} collected
        </span>
      </div>

      <div className="card-grid">
        {cards.map((card) => (
          <CardTile key={card.id} card={card} isNew={starterCardIds.includes(card.id)} />
        ))}
      </div>

      <button className="link-button reset" onClick={onReset}>
        Reset collection to starter pack
      </button>
    </section>
  )
}
