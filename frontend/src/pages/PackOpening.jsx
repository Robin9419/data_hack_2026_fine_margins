import { useRef, useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import CardFace from '../components/CardFace'

// How long the card shakes before it flips (keep in sync with .pack-card.charging in index.css).
const CHARGE_MS = 550

export default function PackOpening() {
  const location = useLocation()
  const navigate = useNavigate()
  const pack = location.state?.pack
  // Per card: 'hidden' -> 'charging' -> 'revealed'
  const [stages, setStages] = useState(() => (pack ?? []).map(() => 'hidden'))
  const started = useRef(new Set())

  if (!pack?.length) return <Navigate to="/" replace />

  const setStage = (i, stage) => setStages((prev) => prev.map((s, j) => (j === i ? stage : s)))

  const reveal = (i) => {
    if (started.current.has(i)) return
    started.current.add(i)
    setStage(i, 'charging')
    setTimeout(() => setStage(i, 'revealed'), CHARGE_MS)
  }

  const revealAll = () => pack.forEach((_, i) => setTimeout(() => reveal(i), i * 250))

  const allRevealed = stages.every((s) => s === 'revealed')
  const newCardIds = pack.filter((c) => c.is_new).map((c) => c.id)

  return (
    <section className="pack-stage">
      <h1>{location.state?.title ?? 'Your starter pack'}</h1>
      <p className="pack-hint">{allRevealed ? 'Nice pull!' : 'Tap a card to find out who you got.'}</p>

      <div className="pack-row">
        {pack.map((card, i) => (
          <button
            key={card.id}
            type="button"
            className={`pack-card ${stages[i]}`}
            style={{ '--delay': `${i * 120}ms` }}
            onClick={() => reveal(i)}
            disabled={stages[i] !== 'hidden'}
            aria-label={`${card.player.first_name} ${card.player.last_name}${stages[i] === 'revealed' ? `, ${card.title ?? 'base card'}` : ', tap to reveal'}`}
          >
            <span className="pack-burst" aria-hidden="true" />
            <CardFace card={card} state={stages[i] === 'revealed' ? 'owned' : 'hidden'} />
            {stages[i] === 'revealed' && (
              <span className={card.is_new ? 'new-tag' : 'dup-tag'}>{card.is_new ? 'NEW' : 'DUPLICATE'}</span>
            )}
            <span className="pack-flash" aria-hidden="true" />
          </button>
        ))}
      </div>

      <div className="pack-actions">
        {allRevealed ? (
          <button type="button" className="pack-button" onClick={() => navigate('/', { state: { newCardIds } })}>
            Go to my collection
          </button>
        ) : (
          <button type="button" className="pack-button secondary" onClick={revealAll}>
            Reveal all
          </button>
        )}
      </div>
    </section>
  )
}
