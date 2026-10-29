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
  { value: 'all', label: 'All teams' },
  ...TEAMS.map((t) => ({ value: t.name, label: t.name })),
]
const TYPE_FILTERS = [
  { value: 'all', label: 'All cards' },
  { value: 'legend', label: 'Legends' },
  { value: 'base', label: 'Base' },
  { value: 'impact', label: 'Impact Specials' },
  { value: 'road', label: 'Ones to Watch' },
  { value: 'collector', label: 'Collector' },
]
// The Impact Specials filter covers the profile and performance specials; Collector also shows the context cards (moment, stadium, trophy).
const FILTER_KINDS = { impact: ['profile', 'performance'], collector: ['collector', 'context'] }
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
  const baseCounts = {} // per club, for a locked collector card's hover info
  for (const c of cards) {
    if (c.type !== 'base') continue
    const t = (baseCounts[c.player.team] ??= { owned: 0, total: 0 })
    t.total += 1
    if (c.owned) t.owned += 1
  }
  // Owned cards first, then locked; within each, by TYPE_ORDER (otherwise API order).
  const shown = cards
    .filter((c) => (team === 'all' || c.player?.team === team) && (type === 'all' || (FILTER_KINDS[type] ?? [type]).includes(c.kind ?? c.type)))
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

      <div className="section-header collection-header">
        <h1>Your collection</h1>
        <span className="progress">
          {ownedCount} / {realCards.length} collected
        </span>
      </div>

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
            <CardTile
              key={card.id}
              card={card}
              club={clubs[card.player?.team]}
              base={card.kind === 'collector' ? baseCounts[card.team] : undefined}
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
