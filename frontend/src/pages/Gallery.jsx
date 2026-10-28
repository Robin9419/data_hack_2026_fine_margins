import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAllCards } from '../allCards'
import { useAuth } from '../auth'
import Activities from '../components/Activities'
import CardSpotlight from '../components/CardSpotlight'
import CardTile from '../components/CardTile'
import { TEAMS, teamOf } from '../teams'
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

export function ChipFilter({ label, options, value, onChange, className = '' }) {
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

// One tile per player (team + jersey) among the shown cards; progress counts all of his cards.
function groupPlayers(shown, cards, playerOf) {
  const keyOf = (c) => (c.type === 'legend' || c.type === 'reward' || !c.player?.jersey ? null : `${c.player.team}|${c.player.jersey}`)
  const groups = new Map()
  for (const c of cards) {
    const key = keyOf(c)
    if (!key) continue
    const g = groups.get(key) ?? { key, total: 0, owned: 0, cardId: c.id, ownedId: null, shown: false, p: null }
    g.total += 1
    if (c.owned) {
      g.owned += 1
      g.ownedId ??= c.id
    }
    const p = playerOf(c)
    if (p?.last_name && (!g.p?.last_name || c.owned)) g.p = p
    g.p ??= p
    groups.set(key, g)
  }
  for (const c of shown) {
    const g = groups.get(keyOf(c) ?? '')
    if (g) g.shown = true
  }
  return [...groups.values()]
    .filter((g) => g.shown)
    .map((g) => ({
      key: g.key,
      cardId: g.ownedId ?? g.cardId,
      owned: g.owned,
      total: g.total,
      team: g.p.team,
      logo: teamOf(g.p.team)?.logo,
      jersey: g.p.jersey,
      first: g.p.first_name,
      last: g.p.last_name ?? 'Locked player',
      position: g.p.position,
      image: g.p.image_url,
    }))
    .sort((a, b) => b.owned - a.owned || a.last.localeCompare(b.last))
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
  const [mode, setMode] = useState(view.mode ?? 'cards')
  const [query, setQuery] = useState(view.query ?? '')
  const allCards = useAllCards()
  const [spotlight, setSpotlight] = useState(null) // special card popped out of the grid
  const closeSpotlight = useCallback(() => setSpotlight(null), [])
  const touchStartX = useRef(null)
  const lastStage = useRef(stage)

  useEffect(() => {
    saveView({ team, type, page, mode, query })
  }, [team, type, page, mode, query])

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
  const fullOf = (c) => allCards?.get(c.id)
  // Locked cards are blanked in the list; the full card has the names.
  const playerOf = (c) => (c.owned ? c.player : fullOf(c)?.player ?? c.player)
  const q = query.trim().toLowerCase()
  const matches = (c) => {
    if (!q) return true
    const p = playerOf(c)
    if (!p) return false
    return [p.first_name, p.last_name, p.jersey && String(p.jersey), p.jersey && `#${p.jersey}`, `${p.first_name ?? ''} ${p.last_name ?? ''}`]
      .some((s) => s && String(s).toLowerCase().includes(q))
  }
  // Owned cards first, then locked; within each, by TYPE_ORDER (otherwise API order).
  const shown = cards
    .filter((c) => (team === 'all' || c.player?.team === team) && (type === 'all' || (c.kind ?? c.type) === type) && matches(c))
    .sort((a, b) => {
      if (a.owned !== b.owned) return a.owned ? -1 : 1
      return TYPE_ORDER[a.type] - TYPE_ORDER[b.type]
    })
  const players = mode === 'players' ? groupPlayers(shown, cards, playerOf) : []
  const items = mode === 'players' ? players : shown
  const pageCount = Math.max(1, Math.ceil(items.length / PAGE_SIZE))
  const current = Math.min(page, pageCount - 1)
  const pageItems = items.slice(current * PAGE_SIZE, (current + 1) * PAGE_SIZE)
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

      <div className="gallery-tools">
        <label className="search">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
            <circle cx="11" cy="11" r="7" />
            <path d="m20 20-3.5-3.5" />
          </svg>
          <input
            type="search"
            value={query}
            placeholder="Search a player or jersey number"
            aria-label="Search a player or jersey number"
            onChange={(e) => {
              setQuery(e.target.value)
              setPage(0)
            }}
          />
          {query && (
            <button type="button" className="clear" aria-label="Clear search" onClick={() => { setQuery(''); setPage(0) }}>
              ×
            </button>
          )}
        </label>
        <div className="seg" role="group" aria-label="View">
          {[['players', 'Players'], ['cards', 'Cards']].map(([value, label]) => (
            <button key={value} type="button" className={mode === value ? 'on' : ''} aria-pressed={mode === value} onClick={() => { setMode(value); setPage(0) }}>
              {label}
            </button>
          ))}
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
          aria-label={mode === 'players' ? 'Previous players' : 'Previous cards'}
          disabled={current === 0}
          onClick={() => goTo(current - 1)}
        >
          ‹
        </button>
        <div className="card-grid" onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}>
          {mode === 'players'
            ? pageItems.map((p) => (
                <Link key={p.key} to={`/players/${p.cardId}`} className={`ptile ${p.owned ? '' : 'unknown'}`}>
                  <div className="ph">
                    {p.image && <img className="photo" src={p.image} alt="" referrerPolicy="no-referrer" loading="lazy" />}
                    {p.logo && <img className="logo" src={p.logo} alt={p.team} />}
                    {p.jersey && <span className="num">{p.jersey}</span>}
                  </div>
                  <div className="body">
                    <b>{p.last}</b>
                    <small>{[p.first, p.position].filter(Boolean).join(' · ')}</small>
                    <div className="dots" aria-label={`${p.owned} of ${p.total} cards`}>
                      {Array.from({ length: p.total }, (_, i) => (
                        <i key={i} className={i < p.owned ? 'on' : ''} />
                      ))}
                      <span>{p.owned}/{p.total}</span>
                    </div>
                  </div>
                </Link>
              ))
            : pageItems.map((card) => (
                <CardTile
                  key={card.id}
                  card={card}
                  club={clubs[card.player?.team]}
                  isNew={newCardIds.includes(card.id)}
                  onOpen={setSpotlight}
                  full={fullOf(card)}
                />
              ))}
        </div>
        <button
          type="button"
          className="pager-arrow next"
          aria-label={mode === 'players' ? 'Next players' : 'Next cards'}
          disabled={current >= pageCount - 1}
          onClick={() => goTo(current + 1)}
        >
          ›
        </button>
      </div>
      {items.length === 0 && <p className="muted">{mode === 'players' ? 'No players match these filters.' : 'No cards match these filters.'}</p>}
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
