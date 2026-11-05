import { useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { formatMatchDate, ordinal } from '../format'
import { teamStyle } from '../teams'
import CardFace, { accentOf } from './CardFace'

const MAX_CLIPS = 3
// Which moments best show off a card, best first. Shots and saves are ranked by xG within their tier.
const KIND_ORDER = ['goal', 'assist', 'save', 'shot', 'faceoff_win', 'goal_against']

// The KPIs behind the archetype (the card's own attributes if the API predates them).
const kpisOf = (card) => card.archetype_kpis ?? card.attributes ?? []

const describe = (m) => `${m.title} at ${m.clock} of the ${m.period_label}. ${m.text}`.trim()

// A Ones to Watch card spans the whole tournament: the pop-out only shows its most recent game with a point on
// video (moments are in game order); the card page lists them all.
function latestGameMoments(card) {
  const moments = card.moments || []
  if (card.kind !== 'road') return moments
  const latest = moments.filter((m) => m.broadcast).at(-1)?.game_id
  return moments.filter((m) => m.game_id === latest)
}

// Up to three clips of the events behind the archetype's KPIs (arena camera first, else the TV replay),
// falling back to the card's own highlight when none of those events are on video.
export function pickClips(card) {
  if (card.type !== 'special') return []
  const moments = latestGameMoments(card)
  const linked = new Set(kpisOf(card).flatMap((a) => a.moment_ids || []))
  const tier = (m) => (KIND_ORDER.includes(m.kind) ? KIND_ORDER.indexOf(m.kind) : KIND_ORDER.length)
  const rank = (m) => tier(m) * 10 - (m.xg || 0)
  const clips = moments
    .filter((m) => linked.has(m.id) && (m.clip || m.broadcast))
    .sort((a, b) => rank(a) - rank(b))
    .slice(0, MAX_CLIPS)
    .map((m) => ({ id: m.id, ...(m.clip || m.broadcast), caption: describe(m) }))
  if (clips.length === 0 && card.video) return [{ id: 'highlight', ...card.video, caption: card.video.description }]
  return clips
}

// Pop-out view of an owned card. It opens on the back: the KPIs that earned a special card its archetype (next to
// clips that show it), or the key facts of a base, legend or reward card. Links on to the player profile.
export default function CardSpotlight({ card, onClose, hideLink = false }) {
  const { pathname } = useLocation()
  const showLink = !hideLink && card.player?.last_name && (card.type === 'base' || card.type === 'special') && !pathname.startsWith('/players/')
  const [flipped, setFlipped] = useState(false)
  // Only special cards have a back (their KPIs). Base, legend and reward cards show everything on the page.
  const flippable = card.type === 'special'
  const profilePath = card.type === 'legend' || card.type === 'reward' ? `/cards/${card.id}/info` : null
  const [clipIndex, setClipIndex] = useState(0)
  const closeRef = useRef(null)
  const clips = pickClips(card)
  const step = (d) => setClipIndex((i) => (i + d + clips.length) % clips.length)

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
      if (clips.length > 1 && e.key === 'ArrowLeft') step(-1)
      if (clips.length > 1 && e.key === 'ArrowRight') step(1)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose, clips.length])

  useEffect(() => {
    document.body.style.overflow = 'hidden'
    closeRef.current?.focus()
    return () => {
      document.body.style.overflow = ''
    }
  }, [])

  const { player } = card
  const clip = clips[clipIndex]
  const name = player?.last_name ? `${player.first_name} ${player.last_name}` : ''
  return (
    <div className="spotlight" role="dialog" aria-modal="true" aria-label={[card.title, name].filter(Boolean).join(': ')} onClick={onClose}>
      <div className="spotlight-panel" onClick={(e) => e.stopPropagation()}>
        <button ref={closeRef} type="button" className="spotlight-close" aria-label="Close" onClick={onClose}>
          ✕
        </button>

        <div className="spotlight-card-col">
          {flippable ? (
            <>
              <button
                type="button"
                className={`spotlight-card ${flipped ? 'flipped' : ''}`}
                onClick={() => setFlipped(!flipped)}
                aria-label={flipped ? 'Show the front of the card' : 'Show the back of the card'}
              >
                <span className="spotlight-flip">
                  <span className="spotlight-front">
                    <CardFace card={card} />
                  </span>
                  <CardBack card={card} />
                </span>
              </button>
              <p className="spotlight-hint">Tap the card to flip it</p>
            </>
          ) : (
            <div className="spotlight-card">
              <CardFace card={card} />
            </div>
          )}
        </div>

        <div className="spotlight-clips">
          {card.type !== 'special' && (
            <>
              <h2>{card.title ?? 'Base card'}</h2>
              {card.type !== 'reward' && (
                <dl className="spotlight-facts">
                  {factsOf(card).all.map(([label, value]) => (
                    <div key={label}>
                      <dt>{label}</dt>
                      <dd>{value}</dd>
                    </div>
                  ))}
                </dl>
              )}
              {card.intro_video && <SpotlightClip clip={{ ...card.intro_video, caption: card.intro_video.description }} />}
            </>
          )}
          {card.type === 'special' && <><div className="spotlight-clips-head">
            <h2>Watch it happen</h2>
            {clips.length > 1 && (
              <span className="spotlight-count">
                {clipIndex + 1} / {clips.length}
              </span>
            )}
          </div>
          {clip ? (
            <div className="spotlight-carousel">
              {clips.length > 1 && (
                <button type="button" className="carousel-arrow prev" aria-label="Previous clip" onClick={() => step(-1)}>
                  ‹
                </button>
              )}
              <SpotlightClip key={clip.id} clip={clip} />
              {clips.length > 1 && (
                <button type="button" className="carousel-arrow next" aria-label="Next clip" onClick={() => step(1)}>
                  ›
                </button>
              )}
            </div>
          ) : (
            <p className="spotlight-empty">No video of this performance in the demo.</p>
          )}</>}
          {clips.length > 1 && (
            <div className="pager-dots spotlight-dots">
              {clips.map((c, i) => (
                <button
                  key={c.id}
                  type="button"
                  className={i === clipIndex ? 'active' : ''}
                  aria-label={`Clip ${i + 1} of ${clips.length}`}
                  aria-current={i === clipIndex ? 'true' : undefined}
                  onClick={() => setClipIndex(i)}
                />
              ))}
            </div>
          )}
          {profilePath && (
            <Link to={profilePath} onClick={onClose} className="spotlight-more">
              <span>
                <strong>{card.type === 'legend' ? 'Legend profile ›' : 'Card profile ›'}</strong>
                <small>{card.type === 'legend' ? `Career, honours and Spengler Cup record of ${name}` : `The story behind ${card.title}`}</small>
              </span>
              <span aria-hidden="true">→</span>
            </Link>
          )}
          {showLink && (
            <Link to={`/players/${card.id}`} onClick={onClose} className="spotlight-more">
              <span>
                <strong>Player profile ›</strong>
                <small>All cards, stats and games of {name}</small>
              </span>
              <span aria-hidden="true">→</span>
            </Link>
          )}
        </div>
      </div>
    </div>
  )
}

// Best in the game, else best on the player's team, else the plain game rank. A KPI from before the tournament
// (Ones to Watch) says which season it is from instead.
function rankText(kpi) {
  if (!kpi.match_rank) return kpi.note ?? null
  if (kpi.match_rank === 1) return 'Best in the game'
  if (kpi.team_rank === 1) return `Best on team · ${ordinal(kpi.match_rank)} in game`
  return `${ordinal(kpi.match_rank)} of ${kpi.players_in_match} ${kpi.rank_pool}`
}

const ageOf = (iso) => {
  const born = new Date(iso)
  const now = new Date()
  const had = now.getMonth() > born.getMonth() || (now.getMonth() === born.getMonth() && now.getDate() >= born.getDate())
  return now.getFullYear() - born.getFullYear() - (had ? 0 : 1)
}

// Label/value facts of a non-special card: `back` (at most 4) for the card back, `all` for the side panel.
function factsOf(card) {
  const bio = card.bio ?? {}
  const p = card.player ?? {}
  const goalie = p.position === 'Goalkeeper'
  const clean = (rows) => rows.filter(([, v]) => v)
  if (card.type === 'base') {
    const born = bio.date_of_birth && `${formatMatchDate(bio.date_of_birth)} (age ${ageOf(bio.date_of_birth)})`
    const height = bio.height_cm && `${bio.height_cm} cm`
    const back = clean([['Position', p.position], ['Born', born], ['Nationality', bio.nationality], ['Height', height]])
    const all = clean([
      ['Team', p.team ?? card.team], ['Position', p.position], ['Nationality', bio.nationality], ['Born', born], ['Birthplace', bio.place_of_birth],
      ['Height', height], ['Weight', bio.weight_kg && `${bio.weight_kg} kg`], [goalie ? 'Catches' : 'Shoots', bio.shoots && (bio.shoots === 'L' ? 'Left' : 'Right')],
      ['College 2025–26', bio.club], ['Draft', bio.draft],
    ])
    return { back, all }
  }
  if (card.type === 'legend') {
    const all = clean([['Position', p.position], ['Nationality', card.legend?.nationality], ['Era', card.legend?.era], ['Years', card.legend?.years]])
    return { back: all.slice(0, 4), all }
  }
  const all = clean([['Earned by', card.unlock], ['Date', card.match?.date && formatMatchDate(card.match.date)], ['Unlocks', card.reward ?? card.title]])
  return { back: all.slice(0, 4), all }
}

// The back of a special card holds the archetype and the KPIs that earned it; other cards show their key facts.
function CardBack({ card }) {
  const style = card.player?.team ? teamStyle(card.player.team) : card.team ? teamStyle(card.team) : undefined
  if (card.type !== 'special') {
    return (
      <span className="spotlight-back card-face compact" style={style}>
        <span className="back-title">{card.title ?? 'Base card'}</span>
        <span className="back-facts">
          {factsOf(card).back.map(([label, value]) => (
            <span key={label} className="back-fact">
              <span className="back-fact-label">{label}</span>
              <span className="back-fact-value">{value}</span>
            </span>
          ))}
        </span>
      </span>
    )
  }
  // Impact specials: tint the whole back orange (Stadium) or purple, like the front, instead of the team colours.
  const accent = accentOf(card)
  const impact = ['profile', 'performance'].includes(card.kind ?? 'profile')
  const tint = impact ? { '--c1': `color-mix(in srgb, ${accent} 38%, #0a0612)` } : {}
  return (
    <span className="spotlight-back card-face" style={{ ...style, ...tint, '--c2': accent }}>
      <span className="back-title">{card.title}</span>
      <span className="back-kpis">
        {kpisOf(card).map((kpi) => (
          <span key={kpi.metric_id} className={`back-kpi ${kpi.match_rank === 1 || kpi.team_rank === 1 ? 'top' : ''}`}>
            <span className="back-kpi-value">
              {kpi.display_value}
              {kpi.unit && <small>{kpi.unit}</small>}
            </span>
            <span className="back-kpi-label">{kpi.label}</span>
            <span className="back-kpi-rank">{rankText(kpi)}</span>
          </span>
        ))}
      </span>
    </span>
  )
}

// A camera clip plays inline; a TV replay shows its thumbnail until clicked, then embeds the YouTube player.
function SpotlightClip({ clip }) {
  const [started, setStarted] = useState(false)
  let media
  if (clip.url) {
    media = <video src={clip.url} poster={clip.poster} controls playsInline preload="none" />
  } else if (started) {
    const params = new URLSearchParams({ autoplay: '1', rel: '0', playsinline: '1', start: String(clip.start) })
    if (clip.end != null) params.set('end', String(clip.end))
    media = (
      <iframe
        src={`https://www.youtube-nocookie.com/embed/${clip.youtube_id}?${params}`}
        title={clip.caption}
        allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
        referrerPolicy="strict-origin-when-cross-origin"
        allowFullScreen
      />
    )
  } else {
    media = (
      <button type="button" className="video-poster" onClick={() => setStarted(true)} aria-label={`Play: ${clip.caption}`}>
        <img src={clip.poster || `https://i.ytimg.com/vi/${clip.youtube_id}/hqdefault.jpg`} alt="" />
        <span className="play">▶</span>
      </button>
    )
  }

  return (
    <figure className="spotlight-clip">
      <div className="video-frame">{media}</div>
      <figcaption>{clip.caption}</figcaption>
    </figure>
  )
}
