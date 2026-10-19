import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import CardFace from '../components/CardFace'
import CardSpotlight from '../components/CardSpotlight'
import { TEAMS } from '../teams'

const KINDS = [
  ['legend', 'Legends'],
  ['base', 'Base'],
  ['profile', 'Profile specials'],
  ['performance', 'Performance specials'],
  ['road', 'Road to Final'],
  ['collector', 'Collector'],
  ['context', 'Moment, stadium, trophy'],
]
const KIND_LABEL = Object.fromEntries(KINDS)
const KIND_ORDER = Object.fromEntries(KINDS.map(([k], i) => [k, i]))
const SOURCES = [
  { value: 'all', label: 'Real and test data' },
  { value: 'real', label: 'Real data only' },
  { value: 'test', label: 'Test data only' },
]
const ALL_TEAMS = TEAMS
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

const caption = (card) => {
  const player = card.player ? `#${card.player.jersey} ${card.player.first_name} ${card.player.last_name}` : card.title
  const what = card.kind === 'base' ? 'Base' : card.title
  return { player, what, game: card.match?.stage }
}

function Select({ label, options, value, onChange }) {
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
  const [spotlight, setSpotlight] = useState(null)
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

  const shown = cards
    .filter(
      (c) =>
        (kind === 'all' || kindOf(c) === kind) &&
        (team === 'all' || c.player?.team === team) &&
        (source === 'all' || (source === 'test') === Boolean(c.test)) &&
        (photos === 'all' || hasActionPhoto(c)),
    )
    .sort(
      (a, b) =>
        KIND_ORDER[kindOf(a)] - KIND_ORDER[kindOf(b)] ||
        (a.player?.team ?? '').localeCompare(b.player?.team ?? '') ||
        (a.player?.jersey ?? 0) - (b.player?.jersey ?? 0),
    )
  const total = (key) => Object.values(counts).reduce((n, r) => n + r[key], 0)

  return (
    <section>
      <h1>All cards</h1>
      <p className="muted small">
        Everything that exists in the app, whether or not a user owns it. Test cards come from the 2025 games without
        Wisehockey data. Tap a special card to flip it.
      </p>

      <table className="admin-counts">
        <thead>
          <tr>
            <th>Kind</th>
            <th>Real data</th>
            <th>Test data</th>
            <th>Total</th>
          </tr>
        </thead>
        <tbody>
          {KINDS.map(([k, label]) => (
            <tr key={k}>
              <th scope="row">{label}</th>
              <td>{counts[k].real}</td>
              <td>{counts[k].test}</td>
              <td>{counts[k].real + counts[k].test}</td>
            </tr>
          ))}
          <tr className="total">
            <th scope="row">All cards</th>
            <td>{total('real')}</td>
            <td>{total('test')}</td>
            <td>{total('real') + total('test')}</td>
          </tr>
        </tbody>
      </table>

      <div className="gallery-filters">
        <Select label="Card type" options={[{ value: 'all', label: 'All kinds' }, ...KINDS.map(([value, label]) => ({ value, label }))]} value={kind} onChange={setKind} />
        <Select label="Team" options={[{ value: 'all', label: 'All teams' }, ...ALL_TEAMS.map((t) => ({ value: t.name, label: t.name }))]} value={team} onChange={setTeam} />
        <Select label="Source" options={SOURCES} value={source} onChange={setSource} />
        <Select label="Photos" options={PHOTOS} value={photos} onChange={setPhotos} />
        <Select label="TEST tag" options={TEST_TAG} value={testTag} onChange={setTestTag} />
        <Select label="Name on specials" options={NAME_LAYOUT} value={nameLayout} onChange={setNameLayout} />
      </div>
      <p className="muted small">
        {shown.length} of {cards.length} cards
      </p>

      <div className="admin-grid">
        {shown.map((card) => {
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
                <span>{player}</span>
                <small className="muted">
                  {KIND_LABEL[kindOf(card)]}
                  {game ? ` · ${game}` : ''}
                </small>
              </figcaption>
            </figure>
          )
        })}
      </div>
      {shown.length === 0 && <p className="muted">No cards match these filters.</p>}

      {spotlight && <CardSpotlight card={spotlight} onClose={closeSpotlight} hideLink />}
    </section>
  )
}
