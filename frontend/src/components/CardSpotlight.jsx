import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ordinal, teamClass } from '../format'
import CardFace from './CardFace'

const MAX_CLIPS = 3
// Which moments best show off a card, best first. Shots and saves are ranked by xG within their tier.
const KIND_ORDER = ['goal', 'assist', 'save', 'shot', 'faceoff_win', 'goal_against']

// The KPIs behind the archetype (the card's own attributes if the API predates them).
const kpisOf = (card) => card.archetype_kpis ?? card.attributes

const describe = (m) => `${m.title} at ${m.clock} of the ${m.period_label}. ${m.text}`.trim()

// Up to three clips of the events behind the archetype's KPIs (arena camera first, else the TV replay),
// falling back to the card's own highlight when none of those events are on video.
function pickClips(card) {
  const moments = card.moments || []
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

// Pop-out view of a special card from the gallery. It opens on the card's back, which shows the KPIs that earned
// the player this archetype, next to clips that show it. Links on to the full card page.
export default function CardSpotlight({ card, onClose }) {
  const [flipped, setFlipped] = useState(true)
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
  return (
    <div className="spotlight" role="dialog" aria-modal="true" aria-label={`${card.title}: ${player.first_name} ${player.last_name}`} onClick={onClose}>
      <div className="spotlight-panel" onClick={(e) => e.stopPropagation()}>
        <button ref={closeRef} type="button" className="spotlight-close" aria-label="Close" onClick={onClose}>
          ✕
        </button>

        <div className="spotlight-card-col">
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
        </div>

        <div className="spotlight-clips">
          <div className="spotlight-clips-head">
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
          )}
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
          <Link to={`/cards/${card.id}`} className="spotlight-more">
            <span>
              <strong>See the full card</strong>
              <small>Every stat, how it ranks and all game events</small>
            </span>
            <span aria-hidden="true">→</span>
          </Link>
        </div>
      </div>
    </div>
  )
}

// Best in the game, else best on the player's team, else the plain game rank.
function rankText(kpi) {
  if (!kpi.match_rank) return null
  if (kpi.match_rank === 1) return 'Best in the game'
  if (kpi.team_rank === 1) return `Best on team · ${ordinal(kpi.match_rank)} in game`
  return `${ordinal(kpi.match_rank)} of ${kpi.players_in_match} ${kpi.rank_pool}`
}

// The back holds only the archetype and the three KPIs that earned it.
function CardBack({ card }) {
  return (
    <span className={`spotlight-back card-face ${teamClass(card.player.team)}`}>
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
