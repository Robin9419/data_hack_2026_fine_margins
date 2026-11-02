import { useRef, useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import CardFace from '../components/CardFace'

// How long the card shakes before it flips (keep in sync with .pack-card.charging in index.css).
const CHARGE_MS = 550

const isCollector = (c) => c.type === 'reward' && c.kind === 'collector'

// Legends and collectors earned by a pack are not part of it: each comes as its own pack after the previous one is
// fully opened.
const EARNED = {
  legend: {
    title: 'Club legend earned!',
    intro: 'You collected enough of a club to earn a legend! Tap a card to find out who you got.',
    done: 'A club legend joined your collection!',
    aria: 'club legend',
  },
  collector: {
    title: 'Collector card earned!',
    intro: 'You collected every base card of a club! Tap a card to find out what you earned.',
    done: 'A collector card joined your collection!',
    aria: 'collector card',
  },
}

export default function PackOpening() {
  const location = useLocation()
  const all = location.state?.pack ?? []
  const main = all.filter((c) => c.type !== 'legend' && !isCollector(c))
  const extras = [
    { kind: 'legend', cards: all.filter((c) => c.type === 'legend') },
    { kind: 'collector', cards: all.filter(isCollector) },
  ].filter((e) => e.cards.length > 0)
  const [step, setStep] = useState(main.length === 0 ? 0 : -1) // -1 is the main pack, then one step per extra pack
  const [seenIds, setSeenIds] = useState([])

  if (!all.length) return <Navigate to="/" replace />

  const fromTrade = location.state?.from === 'trade'
  const advance = (newIds) => {
    setSeenIds(newIds)
    setStep((s) => s + 1)
  }

  if (step >= 0) {
    const extra = extras[step]
    return (
      <Pack
        key={extra.kind}
        pack={extra.cards}
        title={EARNED[extra.kind].title}
        fromTrade={fromTrade}
        earned={EARNED[extra.kind]}
        hasMore={step + 1 < extras.length}
        onMore={advance}
        previousNewIds={seenIds}
      />
    )
  }
  return (
    <Pack
      key="main"
      pack={main}
      title={location.state?.title}
      fromTrade={fromTrade}
      hasMore={extras.length > 0}
      onMore={advance}
    />
  )
}

function Pack({ pack, title, fromTrade, earned, hasMore, onMore, previousNewIds = [] }) {
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

  return (
    <section className="pack-stage">
      <h1>{title ?? 'Your starter pack'}</h1>
      <p className="pack-hint">{!allRevealed
          ? earned
            ? earned.intro
            : 'Tap a card to find out who you got.'
          : earned
            ? earned.done
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
            aria-label={`${card.player ? `${card.player.first_name} ${card.player.last_name}` : card.title}${stages[i] === 'revealed' ? `, ${card.title ?? 'base card'}` : earned ? `, ${earned.aria}, tap to reveal` : ', tap to reveal'}`}
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
            {hasMore ? (
              <button type="button" className="pack-button" onClick={() => onMore(newCardIds)}>
                Continue
              </button>
            ) : (
              <button type="button" className="pack-button" onClick={() => navigate('/', { state: { newCardIds } })}>
                Go to my collection
              </button>
            )}
            {fromTrade && !hasMore && (
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
