import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import CardFace from '../components/CardFace'

const percent = (chance) => `${Math.round(chance * 100)}%`
const fullName = (card) => `${card.player.first_name} ${card.player.last_name}`

// Trade-in: pick three base card copies (duplicates or not) and swap them for one random card. The odds come from
// the backend, so they always match the roll. selected holds one card id per copy, so an id can appear more than once.
export default function Trade() {
  const navigate = useNavigate()
  const { setProgress } = useAuth()
  const [cards, setCards] = useState(null)
  const [info, setInfo] = useState(null)
  const [selected, setSelected] = useState([])
  const [onlySpares, setOnlySpares] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([api.cards(), api.tradeInfo()])
      .then(([data, trade]) => {
        const base = data.cards.filter((c) => c.owned && c.type === 'base')
        setCards(base)
        setInfo(trade)
        setOnlySpares(base.some((c) => c.copies > 1))
      })
      .catch((err) => setError(err.message))
  }, [])

  if (error && !cards) return <p className="error">{error}</p>
  if (!cards || !info) return <p className="muted">Loading your cards…</p>

  const { cost, odds } = info
  const byId = Object.fromEntries(cards.map((c) => [c.id, c]))
  const picked = (id) => selected.filter((s) => s === id).length
  const totalCopies = cards.reduce((n, c) => n + c.copies, 0)
  const spareCount = cards.reduce((n, c) => n + c.copies - 1, 0)
  // Duplicate copies not picked yet, keeping one copy of every card.
  const freeSpares = cards.flatMap((c) => Array(Math.max(0, c.copies - 1 - picked(c.id))).fill(c.id))
  const full = selected.length === cost
  // Cards whose every copy is in the selection leave the collection when traded.
  const leaving = [...new Set(selected)].filter((id) => picked(id) >= byId[id].copies)

  const add = (id) => {
    if (!full && picked(id) < byId[id].copies) setSelected([...selected, id])
  }
  const removeOne = (id) => {
    const i = selected.lastIndexOf(id)
    if (i >= 0) setSelected(selected.filter((_, j) => j !== i))
  }
  const removeAt = (i) => setSelected(selected.filter((_, j) => j !== i))
  const fillWithSpares = () => setSelected([...selected, ...freeSpares].slice(0, cost))

  const onTrade = async () => {
    setBusy(true)
    setError(null)
    try {
      const data = await api.trade(selected)
      setProgress(data.progress)
      const title = data.outcome === 'special' ? 'Special pull!' : 'Your trade-in'
      navigate('/pack', { state: { pack: data.pack, title, from: 'trade' } })
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  const shown = cards
    .filter((c) => !onlySpares || c.copies > 1)
    .sort((a, b) => b.copies - a.copies || fullName(a).localeCompare(fullName(b)))

  return (
    <section className="trade">
      <Link to="/" className="back-link">
        Back to collection
      </Link>

      <div className="trade-machine">
        <h1>Trade-in</h1>
        <p className="trade-lede">Give up any {cost} base cards for one random card.</p>

        <div className="trade-odds" aria-label="What you can get">
          <div className="odds-bar">
            {odds.map((o) => (
              <span key={o.id} className={`odds-seg odds-${o.id}`} style={{ flexGrow: o.chance }} />
            ))}
          </div>
          <ul className="odds-legend">
            {odds.map((o) => (
              <li key={o.id}>
                <span className={`odds-dot odds-${o.id}`} aria-hidden="true" />
                <strong>{percent(o.chance)}</strong> {o.label}
              </li>
            ))}
          </ul>
        </div>

        <div className="trade-slots">
          {Array.from({ length: cost }, (_, i) => {
            const card = byId[selected[i]]
            return card ? (
              <button
                key={i}
                type="button"
                className="trade-slot filled"
                onClick={() => removeAt(i)}
                aria-label={`Remove ${fullName(card)} from the trade`}
              >
                <CardFace card={card} />
                <span className="slot-remove" aria-hidden="true">
                  ✕
                </span>
              </button>
            ) : (
              <div key={i} className="trade-slot empty">
                <span>{i + 1}</span>
              </div>
            )
          })}
        </div>

        {leaving.length > 0 && (
          <div className="trade-warning" role="alert">
            <strong>Heads up: you will no longer own {leaving.length === 1 ? 'this card' : 'these cards'}.</strong>
            <ul>
              {leaving.map((id) => (
                <li key={id}>
                  {fullName(byId[id])}: you are trading {byId[id].copies === 1 ? 'your only copy' : `all ${byId[id].copies} of your copies`}.
                </li>
              ))}
            </ul>
          </div>
        )}
        {error && <p className="trade-error">{error}</p>}

        <div className="pack-actions trade-actions">
          <button type="button" className="pack-button" disabled={!full || busy} onClick={onTrade}>
            {busy ? 'Trading…' : full ? `Trade ${cost} cards` : `Pick ${cost - selected.length} more`}
          </button>
          {!full && freeSpares.length > 0 && (
            <button type="button" className="pack-button secondary" onClick={fillWithSpares}>
              Fill with duplicates
            </button>
          )}
        </div>
      </div>

      {totalCopies < cost ? (
        <p className="muted trade-empty">
          You need at least {cost} base cards to trade. Claim your daily card to collect more.
        </p>
      ) : (
        <>
          <div className="trade-pick-head">
            <h2>Pick your cards</h2>
            <div className="filter-group" role="group" aria-label="Which cards to show">
              <button type="button" className={`filter-chip ${onlySpares ? 'active' : ''}`} onClick={() => setOnlySpares(true)}>
                Duplicates ({spareCount})
              </button>
              <button type="button" className={`filter-chip ${!onlySpares ? 'active' : ''}`} onClick={() => setOnlySpares(false)}>
                All base cards ({cards.length})
              </button>
            </div>
          </div>

          {shown.length === 0 && <p className="muted">No duplicates yet. Show all base cards to trade singles.</p>}
          <div className="card-grid trade-grid">
            {shown.map((card) => {
              const n = picked(card.id)
              const maxed = n >= card.copies || full
              return (
                <div key={card.id} className={`trade-card ${n ? 'picked' : ''} ${n >= card.copies ? 'last-copy' : ''}`}>
                  <button
                    type="button"
                    className="card-tile"
                    onClick={() => add(card.id)}
                    disabled={maxed}
                    aria-label={`Add ${fullName(card)} to the trade (${n} of ${card.copies} picked)`}
                  >
                    {card.copies > 1 && <span className="copies-tag">×{card.copies}</span>}
                    <CardFace card={card} />
                  </button>
                  {n > 0 && (
                    <div className="trade-count">
                      <span>
                        {n} / {card.copies}
                        {n >= card.copies && ' ⚠ all'}
                      </span>
                      <button type="button" aria-label={`Take one ${fullName(card)} out of the trade`} onClick={() => removeOne(card.id)}>
                        −
                      </button>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </>
      )}
    </section>
  )
}
