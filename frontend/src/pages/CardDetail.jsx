import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import AttributeRow from '../components/AttributeRow'
import CardTile from '../components/CardTile'
import InstagramLink from '../components/InstagramLink'
import MomentList from '../components/MomentList'
import PlayerPhoto from '../components/PlayerPhoto'
import VideoSlot from '../components/VideoSlot'
import { formatMatchDate, scoreline } from '../format'
import { teamOf } from '../teams'

export default function CardDetail({ preview = false }) {
  const { id } = useParams()
  const [card, setCard] = useState(null)
  const [error, setError] = useState(null)
  const [playing, setPlaying] = useState(null) // clip picked from a game event
  const [videoOnly, setVideoOnly] = useState(false)
  const videoRef = useRef(null)

  useEffect(() => {
    let active = true
    setCard(null)
    setError(null)
    setPlaying(null)
    setVideoOnly(false)
    const request = preview
      ? api.adminCards().then(({ cards }) => {
          const found = cards.find((card) => card.id === id)
          if (!found) throw new Error('Card not found')
          return found
        })
      : api.card(id)
    request
      .then((card) => { if (active) setCard(card) })
      .catch((err) => { if (active) setError(err.message) })
    return () => { active = false }
  }, [id, preview])

  if (error)
    return (
      <section>
        <Link to={preview ? '/admin' : '/'}>{preview ? '← Back to admin' : '← Back to collection'}</Link>
        <p className="error">{error}</p>
      </section>
    )
  if (!card) return <p className="muted">Loading card…</p>
  if (card.type === 'base') return <BaseCardDetail card={card} />
  if (card.type === 'reward') return <RewardCardDetail card={card} />
  if (card.type === 'legend') return <LegendCardDetail card={card} />

  const { player, match } = card
  const moments = card.moments || []
  // Keep the events in game order, whatever order the metric listed their kinds in.
  const linked = (attr) => attr.moment_ids && moments.filter((m) => attr.moment_ids.includes(m.id))
  const timeline = videoOnly ? moments.filter((m) => m.clip || m.broadcast) : moments
  const filmed = moments.some((m) => m.clip)

  const play = (clip, label) => {
    setPlaying({ ...clip, label, nonce: Date.now() })
    videoRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  return (
    <section className="detail">
      <Link to={preview ? '/admin' : '/'}>{preview ? '← Back to admin' : '← Back to collection'}</Link>

      <header className="detail-header">
        <PlayerPhoto player={player} className="detail-photo" />
        <div className="detail-heading">
          <p className="eyebrow">{card.category ? `${card.category} · ` : ''}{card.title}</p>
          <h1>
            #{player.jersey} {player.first_name} {player.last_name}
          </h1>
          <p className="muted">
            {player.team}
            {player.position ? ` · ${player.position}` : ''}
          </p>
          <InstagramLink player={player} />
          {card.achievement && (
            <div className="achievement">
              <strong>
                {card.achievement.badge} {card.achievement.title}
              </strong>
              <span>{card.achievement.criteria}</span>
            </div>
          )}
        </div>
      </header>

      {match && (
        <div className="match-context">
          <div>
            <span className="label">Match</span>
            {scoreline(match)}
          </div>
          <div>
            <span className="label">Opponent</span>
            {match.opponent}
          </div>
          <div>
            <span className="label">Date</span>
            {formatMatchDate(match.date)}
          </div>
          {match.stage && (
            <div>
              <span className="label">Stage</span>
              {match.stage}
            </div>
          )}
        </div>
      )}

      <h2>Performance</h2>
      <ul className="attributes">
        {card.attributes.map((attr) => (
          <AttributeRow key={attr.metric_id} attr={attr} moments={linked(attr)} onPlay={play} />
        ))}
      </ul>

      <p className="explanation">{card.explanation}</p>

      <h2>Highlight</h2>
      <div ref={videoRef}>
        <VideoSlot video={card.video} playing={playing} onPlay={play} sources={card.video_sources} />
      </div>

      {moments.length > 0 && (
        <>
          <div className="timeline-head">
            <h2>Game events</h2>
            <label className="small">
              <input type="checkbox" checked={videoOnly} onChange={(e) => setVideoOnly(e.target.checked)} /> Only
              moments with video
            </label>
          </div>
          <p className="muted small">
            Every goal, assist, shot{player.position === 'Goalkeeper' ? ', save' : ''} and faceoff win recorded for{' '}
            {player.first_name} {player.last_name} in this match.{' '}
            {filmed
              ? 'Each clip is cut from the arena camera recording of the full game, a few seconds around the event. Goals also have the TV replay.'
              : 'Clips come from the official game highlights, so only goals are on video.'}
          </p>
          <MomentList key={videoOnly} moments={timeline} onPlay={play} limit={8} />
        </>
      )}

      <p className="muted small">
        Source: {card.source} · Edition: {card.edition === 'stadium' ? '🏟 Stadium' : 'Standard'}
      </p>

      {!preview && <PlayerCards cardId={card.id} />}
    </section>
  )
}

// All cards of the player on the page, the ones owned and the ones still locked.
function PlayerCards({ cardId }) {
  const [cards, setCards] = useState(null)

  useEffect(() => {
    let active = true
    setCards(null)
    api
      .playerCards(cardId)
      .then(({ cards }) => { if (active) setCards(cards) })
      .catch(() => { if (active) setCards([]) })
    return () => { active = false }
  }, [cardId])

  const others = cards?.filter((c) => c.id !== cardId)
  if (!others || others.length === 0) return null
  const sorted = [...others].sort((a, b) => (a.owned === b.owned ? 0 : a.owned ? -1 : 1))
  const ownedCount = others.filter((c) => c.owned).length

  return (
    <>
      <h2>Other cards of this player</h2>
      <p className="muted small">
        You own {ownedCount} of {others.length} other cards. Locked cards are still hidden.
      </p>
      <div className="card-grid player-cards">
        {sorted.map((c) => (
          <CardTile key={c.id} card={c} />
        ))}
      </div>
    </>
  )
}

const REWARD_LABEL = { collector: 'Collector card', moment: 'Moment card', stadium: 'Stadium card', trophy: 'Trophy card' }

// Reward cards are earned by owning other cards, not won in the trivia.
function RewardCardDetail({ card }) {
  const { player, match } = card
  return (
    <section className="detail">
      <Link to="/">← Back to collection</Link>

      <header className="detail-header">
        {card.kind === 'collector' ? (
          <div className="detail-photo">
            <img src={teamOf(card.team).logo} alt={card.team} />
          </div>
        ) : card.image_url ? (
          <div className="detail-photo">
            <img src={card.image_url} alt={card.image_alt} referrerPolicy="no-referrer" />
          </div>
        ) : (
          <PlayerPhoto player={player} className="detail-photo" />
        )}
        <div className="detail-heading">
          <p className="eyebrow">{REWARD_LABEL[card.context_type ?? card.kind]}</p>
          <h1>{card.title}</h1>
          <p className="muted">{card.headline ?? card.title}</p>
        </div>
      </header>

      <p className="explanation">{card.text ?? card.explanation}</p>
      <div className="match-context">
        <div>
          <span className="label">How you earned it</span>
          {card.unlock}
        </div>
        <div>
          <span className="label">Match</span>
          {scoreline(match)}
        </div>
        <div>
          <span className="label">Date</span>
          {formatMatchDate(match.date)}
        </div>
      </div>
      {card.club && <AboutInfo heading="About the club" about={card.club} />}
      {card.about && <AboutInfo heading={ABOUT_HEADING[card.context_type]} about={card.about} />}
      <p className="muted small">
        Source: {card.source}
        {card.credit ? ` · Image: ${card.credit}` : ''}
      </p>
    </section>
  )
}

const ABOUT_HEADING = { stadium: 'About the stadium', trophy: 'About the trophy' }

// Background for a reward card (the club, the stadium, the trophy): key facts, its story, lists of facts, sources.
function AboutInfo({ heading, about }) {
  return (
    <>
      <h2>{heading}</h2>
      <div className="match-context">
        {Object.entries(about.facts).map(([label, value]) => (
          <div key={label}>
            <span className="label">{label}</span>
            {value}
          </div>
        ))}
      </div>
      <p className="explanation">{about.summary}</p>

      {Object.entries(about.sections).map(([title, facts]) => (
        <div key={title}>
          <h2>{title}</h2>
          <ul className="legend-facts">
            {facts.map((fact) => (
              <li key={fact}>{fact}</li>
            ))}
          </ul>
        </div>
      ))}

      <p className="muted small">
        Sources: <SourceLinks urls={about.sources} />
      </p>
    </>
  )
}

function SourceLinks({ urls }) {
  return urls.map((url, i) => (
    <span key={url}>
      {i > 0 && ', '}
      <a href={url} target="_blank" rel="noreferrer">
        {new URL(url).hostname.replace(/^www\./, '')}
      </a>
    </span>
  ))
}

const age = (iso) => {
  const born = new Date(iso)
  const now = new Date()
  const hadBirthday =
    now.getMonth() > born.getMonth() || (now.getMonth() === born.getMonth() && now.getDate() >= born.getDate())
  return now.getFullYear() - born.getFullYear() - (hadBirthday ? 0 : 1)
}

// A base card has no archetype or game stats, only the player's profile (from Elite Prospects).
function BaseCardDetail({ card }) {
  const { player, bio, match } = card
  const goalie = player.position === 'Goalkeeper'
  const facts = [
    ['Position', player.position],
    ['Born', bio.date_of_birth && `${formatMatchDate(bio.date_of_birth)} (age ${age(bio.date_of_birth)})`],
    ['Birthplace', bio.place_of_birth],
    ['Nationality', bio.nationality],
    ['Height', bio.height_cm && `${bio.height_cm} cm`],
    ['Weight', bio.weight_kg && `${bio.weight_kg} kg`],
    [goalie ? 'Catches' : 'Shoots', bio.shoots && (bio.shoots === 'L' ? 'Left' : 'Right')],
    ['College 2025–26', bio.club],
    ['Draft', bio.draft],
  ].filter(([, value]) => value)

  return (
    <section className="detail">
      <Link to="/">← Back to collection</Link>

      <header className="detail-header">
        <PlayerPhoto player={player} className="detail-photo" />
        <div className="detail-heading">
          <p className="eyebrow">Base card</p>
          <h1>
            #{player.jersey} {player.first_name} {player.last_name}
          </h1>
          <p className="muted">{player.team}</p>
          <InstagramLink player={player} />
        </div>
      </header>

      <h2>Player profile</h2>
      <div className="match-context">
        {facts.map(([label, value]) => (
          <div key={label}>
            <span className="label">{label}</span>
            {value}
          </div>
        ))}
      </div>

      {match && (
        <p className="muted small">
          Played in {scoreline(match)} on {formatMatchDate(match.date)}.
        </p>
      )}
      <p className="muted small">
        Source:{' '}
        {card.source_url ? (
          <a href={card.source_url} target="_blank" rel="noreferrer">
            {card.source}
          </a>
        ) : (
          card.source
        )}{' '}
        · Edition: {card.edition === 'stadium' ? '🏟 Stadium' : 'Standard'}
      </p>

      <PlayerCards cardId={card.id} />
    </section>
  )
}

// A club legend: no game stats, only why the player is a legend, with their Spengler Cup record first.
function LegendCardDetail({ card }) {
  const { player, legend } = card
  const facts = [
    ['Position', player.position],
    ['Nationality', legend.nationality],
    ['Era', legend.era],
  ].filter(([, value]) => value)

  return (
    <section className="detail legend-detail">
      <Link to="/">← Back to collection</Link>

      <header className="detail-header">
        <figure className="legend-figure">
          <PlayerPhoto player={player} className="detail-photo legend-photo" />
          {legend.moment && <figcaption>{legend.moment}</figcaption>}
        </figure>
        <div className="detail-heading">
          <p className="eyebrow legend-eyebrow">★ Club legend · {player.team}</p>
          <h1>
            {player.jersey ? `#${player.jersey} ` : ''}
            {player.first_name} {player.last_name}
          </h1>
          <InstagramLink player={player} />
          <div className="match-context">
            {facts.map(([label, value]) => (
              <div key={label}>
                <span className="label">{label}</span>
                {value}
              </div>
            ))}
          </div>
        </div>
      </header>

      <h2>Why a legend</h2>
      <p className="explanation">{legend.summary}</p>

      {legend.spengler_cup?.length > 0 && (
        <>
          <h2>At the Spengler Cup</h2>
          <ul className="legend-facts">
            {legend.spengler_cup.map((fact) => (
              <li key={fact}>{fact}</li>
            ))}
          </ul>
        </>
      )}

      {legend.honours?.length > 0 && (
        <>
          <h2>Career honours</h2>
          <ul className="legend-facts">
            {legend.honours.map((fact) => (
              <li key={fact}>{fact}</li>
            ))}
          </ul>
        </>
      )}

      <p className="muted small">
        Earned by collecting {player.team} cards. Photo:{' '}
        {legend.image_source_url ? (
          <a href={legend.image_source_url} target="_blank" rel="noreferrer">
            {legend.image_credit || 'source'}
          </a>
        ) : (
          legend.image_credit || 'none'
        )}
        {legend.sources?.length > 0 && (
          <>
            {' '}
            · Sources: <SourceLinks urls={legend.sources} />
          </>
        )}
      </p>
    </section>
  )
}
