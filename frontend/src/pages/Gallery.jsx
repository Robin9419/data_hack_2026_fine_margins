import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import Activities from '../components/Activities'
import CardSpotlight from '../components/CardSpotlight'
import CardTile from '../components/CardTile'
import { TEAMS } from '../teams'
import { useTournament } from '../tournament'

const PAGE_SIZE = 8
const SWIPE_PX = 50

const TEAM_FILTERS = [
  { value: 'all', label: 'All teams', title: 'All teams' },
  ...TEAMS.map((t) => ({ value: t.name, label: t.short, title: t.name, logo: t.logo })),
]
const TYPE_FILTERS = [
  { value: 'all', label: 'All cards' },
  { value: 'legend', label: 'Legends' },
  { value: 'base', label: 'Base' },
  { value: 'profile', label: 'Profile specials' },
  { value: 'performance', label: 'Performance specials' },
  { value: 'road', label: 'Road to Final' },
  { value: 'collector', label: 'Collector' },
  { value: 'context', label: 'Moment, stadium, trophy' },
]
// Within owned and within locked cards: legends, then special, then reward, then base.
const TYPE_ORDER = { legend: 0, special: 1, reward: 2, base: 3 }

// The filters and page survive a visit to a card's detail page. Per tab, so a new visit starts fresh.
const VIEW_KEY = 'gallery-view'
function readView() {
  try {
    return JSON.parse(sessionStorage.getItem(VIEW_KEY)) ?? {}
  } catch {
    return {}
  }
}
function saveView(view) {
  try {
    sessionStorage.setItem(VIEW_KEY, JSON.stringify(view))
  } catch {
    // Storage can be blocked; the gallery still works without remembering the view.
  }
}

function ChipFilter({ label, options, value, onChange, className = '' }) {
  return (
    <div className="fgroup">
      <span className="fgroup-label" id={`fg-${label}`}>
        {label}
      </span>
      <div className={`chips ${className}`} role="group" aria-labelledby={`fg-${label}`}>
        {options.map((o) => (
          <button
            key={o.value}
            type="button"
            className={`gchip ${value === o.value ? 'active' : ''}`}
            aria-pressed={value === o.value}
            aria-label={o.title ?? o.label}
            title={o.title ?? o.label}
            onClick={() => onChange(o.value)}
          >
            {o.logo && <img src={o.logo} alt="" loading="lazy" />}
            <span>{o.label}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

export default function Gallery() {
  const location = useLocation()
  const navigate = useNavigate()
  const { progress, setProgress } = useAuth()
  const { tournament, refresh: refreshTournament } = useTournament()
  const stage = tournament?.stage
  const newCardIds = location.state?.newCardIds ?? []
  const [cards, setCards] = useState(null)
  const [error, setError] = useState(null)
  const [view] = useState(readView)
  const [team, setTeam] = useState(view.team ?? 'all')
  const [type, setType] = useState(view.type ?? 'all')
  const [page, setPage] = useState(view.page ?? 0)
  const [spotlight, setSpotlight] = useState(null) // special card popped out of the grid
  const closeSpotlight = useCallback(() => setSpotlight(null), [])
  const touchStartX = useRef(null)
  const lastStage = useRef(stage)

  useEffect(() => {
    saveView({ team, type, page })
  }, [team, type, page])

  const load = () =>
    api
      .cards()
      .then((data) => {
        setCards(data.cards)
        setProgress(data.progress)
      })
      .catch((err) => setError(err.message))

  // The cards that exist change with the stage of the tournament timeline.
  useEffect(() => {
    if (!stage) return
    load()
    // Only a change of stage while on the page starts over; the first load keeps the remembered page.
    if (lastStage.current !== undefined && lastStage.current !== stage) setPage(0)
    lastStage.current = stage
  }, [stage])

  const onReset = async () => {
    const data = await api.reset()
    setProgress(data.progress)
    refreshTournament()
    navigate('/pack', { state: { pack: data.pack } })
  }

  if (error) return <p className="error">{error}</p>
  if (!cards) return <p className="muted">Loading cards…</p>

  // Road to Final cards change with every game and are not collected, so they don't count.
  const realCards = cards.filter((c) => c.kind !== 'road')
  const ownedCount = realCards.filter((c) => c.owned).length
  const clubs = Object.fromEntries((progress?.clubs ?? []).map((c) => [c.team, c])) // for a locked legend's hover info
  // Owned cards first, then locked; within each, by TYPE_ORDER (otherwise API order).
  const shown = cards
    .filter((c) => (team === 'all' || c.player?.team === team) && (type === 'all' || (c.kind ?? c.type) === type))
    .sort((a, b) => {
      if (a.owned !== b.owned) return a.owned ? -1 : 1
      return TYPE_ORDER[a.type] - TYPE_ORDER[b.type]
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

      <Activities />

      <div className="collection-header">
        <div>
          <p className="eyebrow">Spengler Cup 2025</p>
          <h1>Your collection</h1>
        </div>
        <div className="progress">
          <strong>
            {ownedCount} / {realCards.length}
          </strong>
          <span>cards collected</span>
        </div>
      </div>

      <div className="gallery-filters">
        <ChipFilter label="Team" options={TEAM_FILTERS} value={team} onChange={filterBy(setTeam)} className="scroll" />
        <ChipFilter label="Card type" options={TYPE_FILTERS} value={type} onChange={filterBy(setType)} />
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
            <CardTile
              key={card.id}
              card={card}
              club={clubs[card.player?.team]}
              isNew={newCardIds.includes(card.id)}
              onOpen={setSpotlight}
            />
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
