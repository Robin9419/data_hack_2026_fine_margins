import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import CardSpotlight from '../components/CardSpotlight'
import CardTile from '../components/CardTile'

const PAGE_SIZE = 8
const SWIPE_PX = 50

const TEAM_FILTERS = [
  { value: 'all', label: 'All teams' },
  { value: 'HIFK', label: 'HIFK' },
  { value: 'Team Canada', label: 'Team Canada' },
  { value: 'HC Davos', label: 'HC Davos' },
  { value: 'HC Sparta Praha', label: 'HC Sparta Praha' },
  { value: 'HC Fribourg-Gottéron', label: 'HC Fribourg-Gottéron' },
  { value: 'U.S. Collegiate Selects', label: 'U.S. Collegiate Selects' },
]
const TYPE_FILTERS = [
  { value: 'all', label: 'All cards' },
  { value: 'special', label: 'Special' },
  { value: 'base', label: 'Base' },
]

function FilterSelect({ label, options, value, onChange }) {
  return (
    <label className="filter-select">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  )
}

export default function Gallery() {
  const location = useLocation()
  const navigate = useNavigate()
  const { setProgress } = useAuth()
  const newCardIds = location.state?.newCardIds ?? []
  const [cards, setCards] = useState(null)
  const [error, setError] = useState(null)
  const [team, setTeam] = useState('all')
  const [type, setType] = useState('all')
  const [page, setPage] = useState(0)
  const [dailyAvailable, setDailyAvailable] = useState(false)
  const [spotlight, setSpotlight] = useState(null) // special card popped out of the grid
  const closeSpotlight = useCallback(() => setSpotlight(null), [])
  const touchStartX = useRef(null)

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
    api.dailyStatus().then((d) => setDailyAvailable(d.available)).catch(() => {})
  }, [])

  const onReset = async () => {
    const data = await api.reset()
    setProgress(data.progress)
    navigate('/pack', { state: { pack: data.pack } })
  }

  const onClaimDaily = async () => {
    try {
      const data = await api.dailyClaim()
      setProgress(data.progress)
      navigate('/pack', { state: { pack: data.pack, title: 'Your daily card' } })
    } catch (err) {
      setDailyAvailable(false)
      setError(err.status === 409 ? null : err.message)
    }
  }

  if (error) return <p className="error">{error}</p>
  if (!cards) return <p className="muted">Loading cards…</p>

  const ownedCount = cards.filter((c) => c.owned).length
  const spareCount = cards.reduce((n, c) => n + (c.type === 'base' && c.copies > 1 ? c.copies - 1 : 0), 0)
  // Owned cards first, then locked; within each, special cards before base (otherwise API order).
  const shown = cards
    .filter((c) => (team === 'all' || c.player.team === team) && (type === 'all' || c.type === type))
    .sort((a, b) => {
      if (a.owned !== b.owned) return a.owned ? -1 : 1
      return a.type === b.type ? 0 : a.type === 'special' ? -1 : 1
    })
  const pageCount = Math.max(1, Math.ceil(shown.length / PAGE_SIZE))
  const current = Math.min(page, pageCount - 1)
  const pageCards = shown.slice(current * PAGE_SIZE, (current + 1) * PAGE_SIZE)
  const goTo = (p) => setPage(Math.max(0, Math.min(pageCount - 1, p)))
  const filterBy = (setter) => (value) => {
    setter(value)
    setPage(0)
  }

  const onTouchStart = (e) => {
    touchStartX.current = e.touches[0].clientX
  }
  const onTouchEnd = (e) => {
    if (touchStartX.current === null) return
    const dx = e.changedTouches[0].clientX - touchStartX.current
    touchStartX.current = null
    if (Math.abs(dx) > SWIPE_PX) goTo(current + (dx < 0 ? 1 : -1))
  }

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

      {dailyAvailable && (
        <button type="button" className="quiz-cta" onClick={onClaimDaily}>
          <span>
            <strong>Your daily card is ready</strong>
            <small>Claim one free base card. A new one is available every day, duplicates included.</small>
          </span>
          <span aria-hidden="true">→</span>
        </button>
      )}

      <Link to="/trade" className="quiz-cta trade-cta">
        <span>
          <strong>Trade in 3 base cards</strong>
          <small>
            {spareCount > 0
              ? `You have ${spareCount} spare ${spareCount === 1 ? 'duplicate' : 'duplicates'}. Swap three for a new card, maybe a special one.`
              : 'Swap any three base cards for a random new card, maybe a special one.'}
          </small>
        </span>
        <span aria-hidden="true">⇄</span>
      </Link>

      <Link to="/quiz" className="quiz-cta">
        <span>
          <strong>Play trivia, win more cards</strong>
          <small>Three questions about the game. Answer at the stadium for the exclusive Stadium edition.</small>
        </span>
        <span aria-hidden="true">→</span>
      </Link>

      <div className="gallery-filters">
        <FilterSelect label="Team" options={TEAM_FILTERS} value={team} onChange={filterBy(setTeam)} />
        <FilterSelect label="Card type" options={TYPE_FILTERS} value={type} onChange={filterBy(setType)} />
      </div>

      <div className="card-pager">
        <button
          type="button"
          className="pager-arrow prev"
          aria-label="Previous cards"
          disabled={current === 0}
          onClick={() => goTo(current - 1)}
        >
          ‹
        </button>
        <div className="card-grid" onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}>
          {pageCards.map((card) => (
            <CardTile key={card.id} card={card} isNew={newCardIds.includes(card.id)} onOpen={setSpotlight} />
          ))}
        </div>
        <button
          type="button"
          className="pager-arrow next"
          aria-label="Next cards"
          disabled={current >= pageCount - 1}
          onClick={() => goTo(current + 1)}
        >
          ›
        </button>
      </div>
      {shown.length === 0 && <p className="muted">No cards match these filters.</p>}
      {pageCount > 1 && (
        <div className="pager-dots">
          {Array.from({ length: pageCount }, (_, i) => (
            <button
              key={i}
              type="button"
              className={i === current ? 'active' : ''}
              aria-label={`Page ${i + 1} of ${pageCount}`}
              aria-current={i === current ? 'page' : undefined}
              onClick={() => goTo(i)}
            />
          ))}
        </div>
      )}

      <button className="link-button reset" onClick={onReset}>
        Reset collection and start over with a new starter pack
      </button>

      {spotlight && <CardSpotlight card={spotlight} onClose={closeSpotlight} />}
    </section>
  )
}
