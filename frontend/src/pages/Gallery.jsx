import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { api, TEST_GAMES_KEY } from '../api'
import { useAuth } from '../auth'
import CardSpotlight from '../components/CardSpotlight'
import CardTile from '../components/CardTile'
import TestDataPanel from '../components/TestDataPanel'
import { TEAMS, TEAMS_2025 } from '../teams'

const PAGE_SIZE = 8
const SWIPE_PX = 50

const loadTestGames = () => {
  try {
    const saved = JSON.parse(localStorage.getItem(TEST_GAMES_KEY))
    return Array.isArray(saved) ? saved : []
  } catch {
    return []
  }
}

const teamFilters = (withTest) => [
  { value: 'all', label: 'All teams' },
  ...[...TEAMS, ...(withTest ? TEAMS_2025 : [])].map((t) => ({ value: t.name, label: t.name })),
]
const TYPE_FILTERS = [
  { value: 'all', label: 'All cards' },
  { value: 'base', label: 'Base' },
  { value: 'profile', label: 'Profile specials' },
  { value: 'performance', label: 'Performance specials' },
  { value: 'road', label: 'Road to Final' },
  { value: 'collector', label: 'Collector' },
  { value: 'context', label: 'Moment, stadium, trophy' },
]
const TYPE_ORDER = { special: 0, reward: 1, base: 2 }

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
  const [testGames, setTestGames] = useState(loadTestGames)
  const [testData, setTestData] = useState(null) // the games that can be switched on
  const [spotlight, setSpotlight] = useState(null) // special card popped out of the grid
  const closeSpotlight = useCallback(() => setSpotlight(null), [])
  const touchStartX = useRef(null)

  const load = () =>
    api
      .cards(testGames)
      .then((data) => {
        setCards(data.cards)
        setProgress(data.progress)
      })
      .catch((err) => setError(err.message))

  useEffect(() => {
    load()
  }, [testGames])

  useEffect(() => {
    api.dailyStatus().then((d) => setDailyAvailable(d.available)).catch(() => {})
    api.testdata().then((d) => setTestData(d.games)).catch(() => {})
  }, [])

  const changeTestGames = (ids) => {
    localStorage.setItem(TEST_GAMES_KEY, JSON.stringify(ids))
    setTestGames(ids)
    setPage(0)
  }

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

  const realCards = cards.filter((c) => !c.test)
  const ownedCount = realCards.filter((c) => c.owned).length
  // Owned cards first, then locked; within each, special cards, then reward cards, then base (otherwise API order).
  const shown = cards
    .filter((c) => (team === 'all' || c.player?.team === team) && (type === 'all' || c.kind === type))
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

      <div className="gallery-header">
        <h1>Your collection</h1>
        <span className="progress">
          {ownedCount} / {realCards.length} collected
        </span>
      </div>

      {dailyAvailable && (
        <button type="button" className="quiz-cta" onClick={onClaimDaily}>
          <span>
            <strong>Your daily card is ready</strong>
            <small>Claim one free base card. A new one is available every day.</small>
          </span>
          <span aria-hidden="true">→</span>
        </button>
      )}

      <Link to="/quiz" className="quiz-cta">
        <span>
          <strong>Play trivia, win more cards</strong>
          <small>Three questions about the game. Answer at the stadium for the exclusive Stadium edition.</small>
        </span>
        <span aria-hidden="true">→</span>
      </Link>

      {testData && <TestDataPanel games={testData} selected={testGames} onChange={changeTestGames} />}

      <div className="gallery-filters">
        <FilterSelect label="Team" options={teamFilters(testGames.length > 0)} value={team} onChange={filterBy(setTeam)} />
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
