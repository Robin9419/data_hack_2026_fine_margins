import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import AttributeRow from '../components/AttributeRow'
import CardTile from '../components/CardTile'
import { formatMatchDate, scoreline } from '../format'
import { nationOf } from '../nations'
import { teamOf } from '../teams'

const hasData = (c) => c.owned && c.type === 'special' && Array.isArray(c.attributes)
const gameOf = (c) => (c.match?.opponent ? `vs ${c.match.opponent}${c.match.date ? ` · ${formatMatchDate(c.match.date)}` : ''}` : null)

export default function PlayerProfile() {
  const { cardId } = useParams()
  const [cards, setCards] = useState(null)
  const [error, setError] = useState(null)
  const [tab, setTab] = useState('cards')

  useEffect(() => {
    let active = true
    setCards(null)
    setError(null)
    setTab('cards')
    api
      .playerCards(cardId)
      .then(({ cards }) => { if (active) setCards(cards) })
      .catch((err) => { if (active) setError(err.message) })
    return () => { active = false }
  }, [cardId])

  if (error)
    return (
      <section>
        <Link to="/">← Back to collection</Link>
        <p className="error">{error}</p>
      </section>
    )
  if (!cards) return <p className="muted">Loading player…</p>
  if (cards.length === 0)
    return (
      <section>
        <Link to="/">← Back to collection</Link>
        <p className="muted">No cards found for this player.</p>
      </section>
    )

  const owned = cards.filter((c) => c.owned)
  const source = owned[0] ?? cards[0]
  const player = owned.find((c) => c.player?.last_name)?.player ?? source.player
  const named = Boolean(player.last_name)
  const base = owned.find((c) => c.bio)
  const nationality = base?.bio?.nationality ?? player.nationality
  const nation = nationOf(nationality)
  const team = teamOf(player.team)
  const photo = player.action_image_url ?? player.image_url
  const lastName = named ? player.last_name : 'Locked player'
  const roles = owned.filter((c) => c.type === 'special' && c.title)
  const sorted = [...cards].sort((a, b) => (a.owned === b.owned ? 0 : a.owned ? -1 : 1))
  const dataCards = owned.filter(hasData)
  const lockedSpecials = cards.filter((c) => !c.owned && c.type === 'special')

  return (
    <section className="pp">
      <div className="pp-hero" style={{ '--pp-bg': photo ? `url("${photo}")` : 'none' }}>
        <nav className="pp-crumbs" aria-label="Breadcrumb">
          <Link to="/">Collection</Link> › <span>{player.team}</span> › <span aria-current="page">{lastName}</span>
        </nav>
        <div className="pp-hero-in">
          <div className="pp-id">
            {team.logo && <img className="pp-logo" src={team.logo} alt={player.team} />}
            {named && <p className="pp-first">{player.first_name}</p>}
            <h1 className="pp-last">{lastName}</h1>
            <ul className="pp-tags">
              {player.jersey && <li>#{player.jersey}</li>}
              {player.position && <li>{player.position}</li>}
              {nationality && (
                <li>
                  {nation && <img src={`https://flagcdn.com/w40/${nation.iso}.png`} alt="" width="18" />} {nationality}
                </li>
              )}
            </ul>
          </div>
          {photo && <div className="pp-photo" aria-hidden="true" />}
          {player.jersey && <span className="pp-number" aria-hidden="true">{player.jersey}</span>}
        </div>
      </div>

      <div className="pp-body">
        <aside className="pp-aside">
          <div className="pp-box">
            <h2>Facts</h2>
            <dl className="pp-facts">
              <dt>Team</dt>
              <dd>{player.team}</dd>
              {player.position && (<><dt>Position</dt><dd>{player.position}</dd></>)}
              {nationality && (<><dt>Nationality</dt><dd>{nationality}</dd></>)}
              {player.jersey && (<><dt>Jersey</dt><dd>#{player.jersey}</dd></>)}
            </dl>
          </div>
          {roles.length > 0 && (
            <div className="pp-box">
              <h2>Roles</h2>
              <ul className="pp-roles">
                {roles.map((c) => (
                  <li key={c.id}>
                    <strong>{c.title}</strong>
                    {gameOf(c) && <span className="muted small">{gameOf(c)}</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </aside>

        <div className="pp-main">
          <div className="pp-tabs" role="tablist" aria-label="Player sections">
            {[['cards', 'Cards'], ['data', 'Match data']].map(([key, label]) => (
              <button
                key={key}
                id={`pp-tab-${key}`}
                role="tab"
                type="button"
                aria-selected={tab === key}
                aria-controls={`pp-panel-${key}`}
                className={tab === key ? 'active' : ''}
                onClick={() => setTab(key)}
              >
                {label}
              </button>
            ))}
          </div>

          {tab === 'cards' && (
            <div id="pp-panel-cards" role="tabpanel" aria-labelledby="pp-tab-cards">
              <div className="pp-box pp-set">
                <div className="pp-set-head">
                  <h2>Player set</h2>
                  <span>{owned.length} of {cards.length} cards</span>
                </div>
                <div className="pp-bar" role="progressbar" aria-valuemin={0} aria-valuemax={cards.length} aria-valuenow={owned.length}>
                  <div style={{ width: `${(owned.length / cards.length) * 100}%` }} />
                </div>
              </div>
              <div className="pp-cards">
                {sorted.map((c) => (
                  <figure key={c.id} className="pp-card">
                    <CardTile card={c} />
                    <figcaption>
                      <strong>{c.owned ? c.title ?? 'Base card' : 'Locked'}</strong>
                      {c.owned && gameOf(c) && <span className="muted small">{gameOf(c)}</span>}
                    </figcaption>
                  </figure>
                ))}
              </div>
            </div>
          )}

          {tab === 'data' && (
            <div id="pp-panel-data" role="tabpanel" aria-labelledby="pp-tab-data">
              {dataCards.length === 0 && <p className="muted">No match data yet. Collect this player's performance cards.</p>}
              {dataCards.map((c) => (
                <article key={c.id} className="pp-box pp-data">
                  <div className="pp-data-card">
                    <CardTile card={c} />
                  </div>
                  <div className="pp-data-body">
                    <h2>{c.title}</h2>
                    {c.match && <p className="muted small">{scoreline(c.match)} · {formatMatchDate(c.match.date)}</p>}
                    {c.explanation && <p className="explanation">{c.explanation}</p>}
                    <ul className="attributes">
                      {c.attributes.map((attr) => (
                        <AttributeRow key={attr.metric_id} attr={attr} />
                      ))}
                    </ul>
                    <Link to={`/cards/${c.id}`}>Open card ›</Link>
                  </div>
                </article>
              ))}
              {lockedSpecials.map((c) => (
                <article key={c.id} className="pp-box pp-data locked">
                  <div className="pp-data-card">
                    <CardTile card={c} />
                  </div>
                  <div className="pp-data-body">
                    <h2>Locked card</h2>
                    <p className="muted">Unlock to see the data.</p>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
