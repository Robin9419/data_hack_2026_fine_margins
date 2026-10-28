import { useCallback, useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { useAllCards } from '../allCards'
import AttributeRow from '../components/AttributeRow'
import CardSpotlight from '../components/CardSpotlight'
import CardTile from '../components/CardTile'
import { formatMatchDate, scoreline } from '../format'
import { nationOf } from '../nations'
import { teamOf } from '../teams'
import { useTournament } from '../tournament'

const hasData = (c) => c.owned && c.type === 'special' && Array.isArray(c.attributes)
const gameOf = (c) => (c.match?.opponent ? `vs ${c.match.opponent}${c.match.date ? ` · ${formatMatchDate(c.match.date)}` : ''}` : null)

const age = (iso) => {
  const born = new Date(iso)
  const now = new Date()
  const hadBirthday =
    now.getMonth() > born.getMonth() || (now.getMonth() === born.getMonth() && now.getDate() >= born.getDate())
  return now.getFullYear() - born.getFullYear() - (hadBirthday ? 0 : 1)
}

const STAGES = { 'Group Torriani': 'Group', 'Group Cattini': 'Group', Quarterfinal: 'QF', Semifinal: 'SF', Final: 'Final' }
const mmss = (s) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}`
const sum = (rows, key) => rows.reduce((t, r) => t + (r[key] ?? 0), 0)
const samePlayer = (a, b) => a.first_name === b.first_name && a.last_name === b.last_name && a.team === b.team

// Static export of backend/scripts/player_games.py; null if it is not there.
let gamesPromise = null
const loadGames = () => (gamesPromise ??= fetch('/data/player-games.json').then((r) => (r.ok ? r.json() : null)).catch(() => null))

function gameStats(rows, goalie) {
  const toi = sum(rows, 'toi')
  const avg = ['Avg. ice time', mmss(toi / rows.length)]
  if (goalie) {
    const sa = sum(rows, 'shots_against')
    return [['Games', rows.length], avg, ['Save %', sa ? `${((sum(rows, 'saves') / sa) * 100).toFixed(1)}%` : '–'],
      ['Goals against avg.', toi ? ((sum(rows, 'goals_against') * 3600) / toi).toFixed(2) : '–']]
  }
  const g = sum(rows, 'goals')
  const a = sum(rows, 'assists')
  const pm = sum(rows, 'plus_minus')
  return [['Games', rows.length], avg, ['Goals + assists', `${g + a} (${g}+${a})`], ['Shots', sum(rows, 'shots')],
    ['Plus/minus', pm > 0 ? `+${pm}` : pm], ['Penalty min.', sum(rows, 'pim')]]
}

const TIPS = {
  'Games': 'Games he played in the tournament.',
  'Avg. ice time': 'Average time on the ice per game played (minutes:seconds).',
  'Goals + assists': 'Goals plus assists in the tournament (goals+assists).',
  'Shots': 'Shots on goal.',
  'Plus/minus': 'Goals for minus goals against while he was on the ice at even strength or shorthanded.',
  'Penalty min.': 'Total penalty minutes served.',
  'Save %': 'Share of shots on goal he stopped.',
  'Goals against avg.': 'Goals conceded per 60 minutes.',
}

function Info({ id, text }) {
  return (
    <span className="pp-info" tabIndex={0} aria-describedby={id}>
      <svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" strokeWidth="1.3" /><path d="M8 7v4.2M8 4.6v.1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
      <span id={id} className="pp-tip" role="tooltip">{text}</span>
    </span>
  )
}

export default function PlayerProfile() {
  const { cardId } = useParams()
  const allCards = useAllCards()
  const { tournament } = useTournament()
  const stage = tournament?.stage
  const [cards, setCards] = useState(null)
  const [error, setError] = useState(null)
  const [tab, setTab] = useState('cards')
  const [games, setGames] = useState(null)
  const [scrollTo, setScrollTo] = useState(null)
  const [widePhoto, setWidePhoto] = useState(false)
  const [spotlight, setSpotlight] = useState(null)
  const [params, setParams] = useSearchParams()
  const closeSpotlight = useCallback(() => setSpotlight(null), [])

  // ?card=<id> opens that card's spotlight once; the param is dropped right away.
  useEffect(() => {
    const id = params.get('card')
    if (!id || !cards) return
    const found = cards.find((c) => c.id === id && c.owned)
    if (found) setSpotlight(found)
    setParams((p) => { p.delete('card'); return p }, { replace: true })
  }, [cards, params])
  useEffect(() => { loadGames().then(setGames) }, [])
  useEffect(() => {
    if (tab !== 'data' || !scrollTo) return
    document.getElementById(`pp-data-${scrollTo}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    setScrollTo(null)
  }, [tab, scrollTo])

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
  }, [cardId, stage])

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
  const availableIds = new Set(cards.map((c) => c.id))
  const ownedIds = new Set(owned.map((c) => c.id))
  const source = owned[0] ?? cards[0]
  const who = allCards?.get(cardId)?.player ?? owned.find((c) => c.player?.last_name)?.player ?? source.player
  // Only cards that exist at the user's stage (owned or still locked); what comes later is not shown.
  const everyCard = allCards
    ? [...allCards.values()].filter((c) => c.type !== 'reward' && c.player && samePlayer(c.player, who) && availableIds.has(c.id))
    : []
  const list = everyCard.length > 0
    ? everyCard.map((c) => ({
        card: ownedIds.has(c.id) ? owned.find((o) => o.id === c.id) : { ...(cards.find((x) => x.id === c.id) ?? c), owned: false },
        full: c,
        status: ownedIds.has(c.id) ? 'owned' : 'locked',
      }))
    : cards.map((c) => ({ card: c, full: allCards?.get(c.id), status: c.owned ? 'owned' : 'locked' }))
  const rank = { owned: 0, locked: 1 }
  const sorted = [...list].sort((a, b) => rank[a.status] - rank[b.status])
  const availableCount = list.length
  const player = everyCard.find((c) => c.player.last_name)?.player ?? owned.find((c) => c.player?.last_name)?.player ?? source.player
  const named = Boolean(player.last_name)
  const base = everyCard.find((c) => c.bio) ?? owned.find((c) => c.bio)
  const nationality = base?.bio?.nationality ?? player.nationality
  const nation = nationOf(nationality)
  const team = teamOf(player.team)
  const photo = player.action_image_url ?? player.image_url
  const bio = base?.bio ?? {}
  const goalie = player.position === 'Goalkeeper'
  const bioFacts = [
    ['Born', bio.date_of_birth && `${formatMatchDate(bio.date_of_birth)} (age ${age(bio.date_of_birth)})`],
    ['Birthplace', bio.place_of_birth],
    ['Height', bio.height_cm && `${bio.height_cm} cm`],
    ['Weight', bio.weight_kg && `${bio.weight_kg} kg`],
    [goalie ? 'Catches' : 'Shoots', bio.shoots && (bio.shoots === 'L' ? 'Left' : 'Right')],
    ['College 2025–26', bio.club],
    ['Draft', bio.draft],
  ].filter(([, value]) => value)
  const lastName = named ? player.last_name : 'Locked player'
  const dataCards = owned.filter(hasData)
  const lockedSpecials = list.filter((x) => x.status !== 'owned' && x.card.type === 'special')
  const playedIds = new Set((tournament?.results ?? []).map((r) => r.id))
  const playerGames = games?.[`${player.team}#${player.jersey}`]?.filter((g) => playedIds.has(g.game))
  const stats = playerGames?.length ? gameStats(playerGames, goalie) : null
  const gameCards = (g) => everyCard.filter((c) => c.type === 'special' && c.kind !== 'road' && c.title && c.match?.id === g.game && c.match.date === g.date)

  return (
    <section className="pp">
      <div className={`pp-hero ${player.action_image_url || widePhoto ? '' : 'portrait'}`} style={{ '--pp-bg': photo ? `url("${photo}")` : 'none' }}>
        <div className="pp-hero-in">
          <div className="pp-id">
            {named && <p className="pp-first">{player.first_name}</p>}
            <h1 className="pp-last">{lastName}</h1>
            <ul className="pp-tags">
              {team.logo && (
                <li className="pp-logo-pill">
                  <img className="pp-logo" src={team.logo} alt="" />
                  {player.team}
                </li>
              )}
              {player.jersey && <li>#{player.jersey}</li>}
              {player.position && <li>{player.position}</li>}
              {nationality && (
                <li>
                  {nation && <img src={`https://flagcdn.com/w40/${nation.iso}.png`} alt="" width="18" />} {nationality}
                </li>
              )}
            </ul>
            {bioFacts.length > 0 && (
              <dl className="pp-master">
                {bioFacts.map(([k, v]) => (<div key={k}><dt>{k}</dt><dd>{v}</dd></div>))}
              </dl>
            )}
          </div>
          {photo && <div className="pp-photo" aria-hidden="true" />}
          {/* Some image_urls are already landscape action shots: show those wide like an action image. */}
          {photo && <img src={photo} alt="" hidden onLoad={(e) => setWidePhoto(e.currentTarget.naturalWidth / e.currentTarget.naturalHeight > 1.15)} />}
        </div>
        <div className="pp-foot">
          {stats && (
            <div className="pp-tourn">
              <h2>Spengler Cup 2025</h2>
              <dl className="pp-stats">
                {stats.map(([k, v]) => (
                  <div key={k}>
                    <dd>{v}</dd>
                    <dt>{k} <Info id={`pp-tip-${k.replace(/\W+/g, '')}`} text={TIPS[k]} /></dt>
                  </div>
                ))}
              </dl>
            </div>
          )}
          <div className="pp-set">
            <span className="pp-set-label">
              Player set {owned.length} of {availableCount} cards
            </span>
            <div className="pp-bar" role="progressbar" aria-label="Player set" aria-valuemin={0} aria-valuemax={availableCount} aria-valuenow={owned.length}>
              <div style={{ width: `${availableCount ? (owned.length / availableCount) * 100 : 0}%` }} />
            </div>
          </div>
        </div>
      </div>

      {playerGames?.length > 0 && (
        <ul className="pp-strip" aria-label="Games">
          {playerGames.map((g) => {
            const home = g.home_team === player.team
            const opp = teamOf(g.opponent)
            const chips = gameCards(g)
            const line = goalie ? `${g.saves ?? 0} sv` : `${g.goals}+${g.assists}`
            const open = (c) => { setTab('data'); setScrollTo(c.id) }
            return (
              <li key={g.game} className="pp-game">
                <span className="pp-game-top">
                  <span className="pp-game-opp">
                    {opp.logo && <img src={opp.logo} alt="" width="16" height="16" />} {opp.short || g.opponent}
                  </span>
                  <span className={`pp-game-res ${g.won ? 'won' : 'lost'}`} title={g.won ? 'Won' : 'Lost'}>
                    {home ? g.home_score : g.away_score}–{home ? g.away_score : g.home_score}
                  </span>
                </span>
                <span className="pp-game-bot">
                  <span className="pp-game-date">{formatMatchDate(g.date).replace(/\s*\d{4}$/, '')}</span>
                  <span className="pp-game-line" title={goalie ? 'Saves' : 'Goals + assists'}>{line}</span>
                  {chips.map((c) => (
                    <button key={c.id} type="button" className="pp-chip" onClick={() => open(c)}>{c.title}</button>
                  ))}
                </span>
              </li>
            )
          })}
        </ul>
      )}

      <div className="pp-body">
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
              <div className="pp-cards">
                {sorted.map(({ card: c, full, status }) => (
                  <figure key={c.id} className="pp-card">
                    <CardTile card={c} full={full} onOpen={setSpotlight} />
                    <figcaption>
                      <strong>{status === 'owned' ? c.title ?? 'Base card' : 'Locked'}</strong>
                      {status === 'owned' && c.type === 'special' && gameOf(c) && <span className="muted small">{gameOf(c)}</span>}
                    </figcaption>
                  </figure>
                ))}
              </div>
            </div>
          )}

          {tab === 'data' && (
            <div id="pp-panel-data" role="tabpanel" aria-labelledby="pp-tab-data">
              {dataCards.length === 0 && (
                <div className="pp-box">
                  <h2>No match data yet</h2>
                  <p className="muted">
                    Performance cards show the numbers behind a player's game. Collect this player's special cards
                    {lockedSpecials.length > 0 ? ' (shown below)' : ''} and their match data appears here.
                  </p>
                  <button type="button" className="pp-chip" onClick={() => setTab('cards')}>See all cards of this player</button>
                </div>
              )}
              {dataCards.map((c) => (
                <article key={c.id} id={`pp-data-${c.id}`} className="pp-box pp-data">
                  <div className="pp-data-card">
                    <CardTile card={c} onOpen={setSpotlight} />
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
                    <button type="button" className="link-button" onClick={() => setSpotlight(c)}>Open card ›</button>
                  </div>
                </article>
              ))}
              {lockedSpecials.map(({ card: c, full }) => (
                <article key={c.id} id={`pp-data-${c.id}`} className="pp-box pp-data locked">
                  <div className="pp-data-card">
                    <CardTile card={c} full={full} />
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
      {spotlight && <CardSpotlight card={spotlight} onClose={closeSpotlight} />}
    </section>
  )
}
