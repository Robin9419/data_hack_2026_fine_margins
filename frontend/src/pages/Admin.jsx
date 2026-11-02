import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import CardFace from '../components/CardFace'
import CardSpotlight from '../components/CardSpotlight'
import { TEAMS, teamOf, teamStyle } from '../teams'
import Dropdown from '../components/Dropdown'

const KINDS = [
  ['legend', 'Legends'],
  ['base', 'Base'],
  ['profile', 'Profile specials'],
  ['performance', 'Performance specials'],
  ['road', 'Ones to Watch'],
  ['collector', 'Collector'],
  ['context', 'Moment, stadium, trophy'],
]
const KIND_LABEL = Object.fromEntries(KINDS)
const KIND_ORDER = Object.fromEntries(KINDS.map(([k], i) => [k, i]))
const PAGE_SIZE = 8
const POS_SHORT = { Forward: 'FWD', Defender: 'DEF', Goalkeeper: 'GK' }
const KIND_FILTERS = [{ value: 'all', label: 'All kinds' }, ...KINDS.map(([value, label]) => ({ value, label }))]
const TEAM_FILTERS = [
  { value: 'all', label: 'All teams', title: 'All teams' },
  ...TEAMS.map((t) => ({ value: t.name, label: t.short, title: t.name, logo: t.logo })),
]
const SOURCES = [
  { value: 'all', label: 'Real and test data' },
  { value: 'real', label: 'Real data only' },
  { value: 'test', label: 'Test data only' },
]
const PHOTOS = [
  { value: 'all', label: 'All cards' },
  { value: 'action', label: 'Action photos only' },
]
const TEST_TAG = [
  { value: 'show', label: 'Show' },
  { value: 'hide', label: 'Hide' },
]
const NAME_LAYOUT = [
  { value: 'vertical', label: 'Vertical' },
  { value: 'horizontal', label: 'Horizontal' },
]
const hasActionPhoto = (c) => c.kind === 'performance' && Boolean(c.player?.action_image_url)

const kindOf = (c) => c.kind ?? c.type
// Legends and rewards have no player profile page.
const hasProfile = (c) => c.type !== 'legend' && c.type !== 'reward' && Boolean(c.player?.jersey)
const playerKey = (c) => `${c.player.team}|${c.player.jersey}`

const caption = (card) => {
  const player = card.player ? `${card.player.jersey != null ? `#${card.player.jersey} ` : ''}${card.player.first_name} ${card.player.last_name}` : card.title
  const what = card.kind === 'base' ? 'Base' : card.title
  return { player, what, game: card.match?.stage }
}

// One tile per player (team + jersey) among the shown cards.
function groupPlayers(shown) {
  const groups = new Map()
  for (const c of shown) {
    if (!hasProfile(c)) continue
    const g = groups.get(playerKey(c)) ?? { key: playerKey(c), cardId: c.id, count: 0, p: c.player }
    g.count += 1
    if (!g.p.last_name && c.player.last_name) g.p = c.player
    groups.set(g.key, g)
  }
  return [...groups.values()].sort((a, b) => (a.p.team ?? '').localeCompare(b.p.team ?? '') || a.p.jersey - b.p.jersey)
}

// Every card that exists after the whole tournament, regardless of what the user owns or where they are on the
// timeline: the card set, including the test cards of all 2025 games.
export default function Admin() {
  const [cards, setCards] = useState(null)
  const [error, setError] = useState(null)
  const [kind, setKind] = useState('all')
  const [team, setTeam] = useState('all')
  const [source, setSource] = useState('all')
  const [photos, setPhotos] = useState('all')
  const [testTag, setTestTag] = useState('show')
  const [nameLayout, setNameLayout] = useState('vertical')
  const [mode, setMode] = useState('cards')
  const [query, setQuery] = useState('')
  const [spotlight, setSpotlight] = useState(null)
  const [page, setPage] = useState(0)
  const touchStartX = useRef(null)
  // Any change of filters, search or view starts again on the first page.
  useEffect(() => setPage(0), [kind, team, source, photos, mode, query])
  const closeSpotlight = useCallback(() => setSpotlight(null), [])

  useEffect(() => {
    api
      .adminCards()
      .then((d) => setCards(d.cards))
      .catch((err) => setError(err.message))
  }, [])

  const counts = useMemo(() => {
    const rows = Object.fromEntries(KINDS.map(([k]) => [k, { real: 0, test: 0 }]))
    for (const c of cards ?? []) rows[kindOf(c)][c.test ? 'test' : 'real'] += 1
    return rows
  }, [cards])

  if (error) return <p className="error">{error}</p>
  if (!cards) return <p className="muted">Loading all cards…</p>

  const q = query.trim().toLowerCase()
  const matches = (c) => {
    if (!q) return true
    const p = c.player
    return [p?.first_name, p?.last_name, p?.jersey && String(p.jersey), p?.jersey && `#${p.jersey}`, p && `${p.first_name ?? ''} ${p.last_name ?? ''}`, c.title]
      .some((s) => s && String(s).toLowerCase().includes(q))
  }
  const shown = cards
    .filter(
      (c) =>
        (kind === 'all' || kindOf(c) === kind) &&
        (team === 'all' || c.player?.team === team) &&
        (source === 'all' || (source === 'test') === Boolean(c.test)) &&
        (photos === 'all' || hasActionPhoto(c)) &&
        matches(c),
    )
    .sort(
      (a, b) =>
        KIND_ORDER[kindOf(a)] - KIND_ORDER[kindOf(b)] ||
        (a.player?.team ?? '').localeCompare(b.player?.team ?? '') ||
        (a.player?.jersey ?? 0) - (b.player?.jersey ?? 0),
    )
  const players = mode === 'players' ? groupPlayers(shown) : []
  const items = mode === 'players' ? players : shown
  const pageCount = Math.max(1, Math.ceil(items.length / PAGE_SIZE))
  const current = Math.min(page, pageCount - 1)
  const pageItems = items.slice(current * PAGE_SIZE, (current + 1) * PAGE_SIZE)
  const goTo = (p) => setPage(Math.max(0, Math.min(pageCount - 1, p)))
  const onTouchStart = (e) => { touchStartX.current = e.touches[0].clientX }
  const onTouchEnd = (e) => {
    if (touchStartX.current === null) return
    const dx = e.changedTouches[0].clientX - touchStartX.current
    touchStartX.current = null
    if (Math.abs(dx) > 50) goTo(current + (dx < 0 ? 1 : -1))
  }
  const total = (key) => Object.values(counts).reduce((n, r) => n + r[key], 0)

  return (
    <section>
      <div className="collection-header">
        <div>
          <p className="eyebrow">Admin</p>
          <h1 className="admin-title">All cards</h1>
        </div>
      </div>
      <p className="muted small">
        Everything that exists in the app, whether or not a user owns it. Test cards come from the 2025 games without
        Wisehockey data. Tap a special card to flip it.
      </p>

      <div className="stat-tiles">
        <div className="stat-tile total">
          <span className="stat-label">All cards</span>
          <strong>{total('real') + total('test')}</strong>
          <small>
            {total('real')} real · {total('test')} test
          </small>
        </div>
        {KINDS.map(([k, label]) => (
          <div key={k} className="stat-tile">
            <span className="stat-label">{label}</span>
            <strong>{counts[k].real + counts[k].test}</strong>
            <small>
              {counts[k].real} real · {counts[k].test} test
            </small>
          </div>
        ))}
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
            onChange={(e) => setQuery(e.target.value)}
          />
          {query && (
            <button type="button" className="clear" aria-label="Clear search" onClick={() => setQuery('')}>
              ×
            </button>
          )}
        </label>
        <div className="seg" role="group" aria-label="View">
          {[['players', 'Players'], ['cards', 'Cards']].map(([value, label]) => (
            <button key={value} type="button" className={mode === value ? 'on' : ''} aria-pressed={mode === value} onClick={() => setMode(value)}>
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="dd-row">
        <Dropdown label="Team" options={TEAM_FILTERS} value={team} onChange={setTeam} />
        <Dropdown label="Card type" options={KIND_FILTERS} value={kind} onChange={setKind} />
        <Dropdown label="Source" options={SOURCES} value={source} onChange={setSource} />
        <Dropdown label="Photos" options={PHOTOS} value={photos} onChange={setPhotos} />
        <Dropdown label="TEST tag" options={TEST_TAG} value={testTag} onChange={setTestTag} />
        <Dropdown label="Name on specials" options={NAME_LAYOUT} value={nameLayout} onChange={setNameLayout} />
      </div>
      <p className="muted small">
        {mode === 'players' ? `${players.length} players · ` : ''}
        {shown.length} of {cards.length} cards
      </p>

      <div className="card-pager">
        <button type="button" className="pager-arrow prev" aria-label="Previous page" disabled={current === 0} onClick={() => goTo(current - 1)}>
          ‹
        </button>
        <div className="card-grid admin-page" onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}>
          {mode === 'players'
            ? pageItems.map(({ key, cardId, count, p }) => (
                <Link key={key} to={`/players/${cardId}`} className="ptile" style={teamStyle(p.team)}>
                  <div className="ph">
                    {p.image_url && <img className="photo" src={p.image_url} alt="" referrerPolicy="no-referrer" loading="lazy" />}
                  </div>
                  <div className="pt-corner">
                    {teamOf(p.team)?.logo && <span className="pt-logo"><img src={teamOf(p.team).logo} alt={p.team} /></span>}
                    {p.position && <span className="pt-pos">{POS_SHORT[p.position] ?? p.position}</span>}
                  </div>
                  <div className="body">
                    {p.first_name && <small className="pt-first">{p.first_name}</small>}
                    <b>{p.last_name ?? 'Player'}</b>
                    <p className="pt-meta">
                      {p.jersey && <span className="pt-no"><span><small>#</small>{p.jersey}</span></span>}
                      <span className="pt-team">{count} {count === 1 ? 'card' : 'cards'}</span>
                    </p>
                  </div>
                </Link>
              ))
            : pageItems.map((card) => {
                const { player, what, game } = caption(card)
                const face = (
                  <>
                    {card.test && testTag === 'show' && <span className="test-tag">TEST</span>}
                    <CardFace card={card} nameLayout={nameLayout} />
                  </>
                )
                return (
                  <figure key={card.id} className="admin-cell">
                    {card.type === 'special' ? (
                      <button type="button" className="card-tile" onClick={() => setSpotlight(card)}>
                        {face}
                      </button>
                    ) : (
                      <div className="card-tile">{face}</div>
                    )}
                    <figcaption>
                      <strong>{what}</strong>
                      {hasProfile(card) ? (
                        <Link to={`/players/${card.id}`} className="plain-link">
                          {player}
                        </Link>
                      ) : (
                        <span>{player}</span>
                      )}
                      <small className="muted">
                        {KIND_LABEL[kindOf(card)]}
                        {game ? ` · ${game}` : ''}
                      </small>
                      <span className="admin-links">
                        <Link to={`/admin/cards/${card.id}`}>Preview ›</Link>
                        {hasProfile(card) && <Link to={`/players/${card.id}`}>Profile ›</Link>}
                      </span>
                    </figcaption>
                  </figure>
                )
              })}
        </div>
        <button type="button" className="pager-arrow next" aria-label="Next page" disabled={current >= pageCount - 1} onClick={() => goTo(current + 1)}>
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

      {spotlight && <CardSpotlight card={spotlight} onClose={closeSpotlight} hideLink />}
    </section>
  )
}
