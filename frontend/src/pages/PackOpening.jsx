import { useRef, useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import CardFace from '../components/CardFace'

// How long the card shakes before it flips (keep in sync with .pack-card.charging in index.css).
const CHARGE_MS = 550

// Legends earned by a pack are not part of it: they come as their own pack after the first one is fully opened.
export default function PackOpening() {
  const location = useLocation()
  const all = location.state?.pack ?? []
  const legends = all.filter((c) => c.type === 'legend')
  const main = all.filter((c) => c.type !== 'legend')
  const [showLegends, setShowLegends] = useState(main.length === 0)
  const [seenIds, setSeenIds] = useState([])

  if (!all.length) return <Navigate to="/" replace />

  if (showLegends) {
    return (
      <Pack
        key="legends"
        pack={legends}
        title="Club legend earned!"
        fromTrade={location.state?.from === 'trade'}
        legendPack
        previousNewIds={seenIds}
      />
    )
  }
  return (
    <Pack
      key="main"
      pack={main}
      title={location.state?.title}
      fromTrade={location.state?.from === 'trade'}
      hasLegends={legends.length > 0}
      onLegends={(newIds) => {
        setSeenIds(newIds)
        setShowLegends(true)
      }}
    />
  )
}

function Pack({ pack, title, fromTrade, legendPack, hasLegends, onLegends, previousNewIds = [] }) {
  const navigate = useNavigate()
  // Per card: 'hidden' -> 'charging' -> 'revealed'
  const [stages, setStages] = useState(() => (pack ?? []).map(() => 'hidden'))
  const started = useRef(new Set())

  const setStage = (i, stage) => setStages((prev) => prev.map((s, j) => (j === i ? stage : s)))

  const reveal = (i) => {
    if (started.current.has(i)) return
    started.current.add(i)
    setStage(i, 'charging')
    setTimeout(() => setStage(i, 'revealed'), CHARGE_MS)
  }

  const revealAll = () => pack.forEach((_, i) => setTimeout(() => reveal(i), i * 250))

  const allRevealed = stages.every((s) => s === 'revealed')
  const newCardIds = [...previousNewIds, ...pack.filter((c) => c.is_new).map((c) => c.id)]
  const special = pack.some((c) => c.type === 'special')
  const legend = !!legendPack

  return (
    <section className="pack-stage">
      <h1>{title ?? 'Your starter pack'}</h1>
      <p className="pack-hint">{!allRevealed
          ? legend
            ? 'You collected enough of a club to earn a legend! Tap a card to find out who you got.'
            : 'Tap a card to find out who you got.'
          : legend
            ? 'A club legend joined your collection!'
            : special
              ? 'A special card!'
              : 'Nice pull!'}</p>

      <div className="pack-row">
        {pack.map((card, i) => (
          <button
            key={`${card.id}-${i}`}
            type="button"
            className={`pack-card ${stages[i]} ${card.type === 'base' ? '' : card.type}`}
            style={{ '--delay': `${i * 120}ms` }}
            onClick={() => reveal(i)}
            disabled={stages[i] !== 'hidden'}
            aria-label={`${card.player.first_name} ${card.player.last_name}${stages[i] === 'revealed' ? `, ${card.title ?? 'base card'}` : card.type === 'legend' ? ', club legend, tap to reveal' : ', tap to reveal'}`}
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
          <>
            {hasLegends ? (
              <button type="button" className="pack-button" onClick={() => onLegends(newCardIds)}>
                Continue
              </button>
            ) : (
              <button type="button" className="pack-button" onClick={() => navigate('/', { state: { newCardIds } })}>
                Go to my collection
              </button>
            )}
            {fromTrade && !hasLegends && (
              <button type="button" className="pack-button secondary" onClick={() => navigate('/trade')}>
                Trade again
              </button>
            )}
          </>
        ) : (
          <button type="button" className="pack-button secondary" onClick={revealAll}>
            Reveal all
          </button>
        )}
      </div>
    </section>
  )
}
