import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import AttributeRow from '../components/AttributeRow'
import MomentList from '../components/MomentList'
import PlayerPhoto from '../components/PlayerPhoto'
import VideoSlot from '../components/VideoSlot'
import { formatMatchDate, scoreline } from '../format'

export default function CardDetail() {
  const { id } = useParams()
  const [card, setCard] = useState(null)
  const [error, setError] = useState(null)
  const [playing, setPlaying] = useState(null) // clip picked from a game event
  const [videoOnly, setVideoOnly] = useState(false)
  const videoRef = useRef(null)

  useEffect(() => {
    setPlaying(null)
    api
      .card(id)
      .then(setCard)
      .catch((err) => setError(err.message))
  }, [id])

  if (error)
    return (
      <section>
        <Link to="/">← Back to collection</Link>
        <p className="error">{error}</p>
      </section>
    )
  if (!card) return <p className="muted">Loading card…</p>

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
      <Link to="/">← Back to collection</Link>

      <header className="detail-header">
        <PlayerPhoto player={player} className="detail-photo" />
        <div className="detail-heading">
          <p className="eyebrow">{card.title}</p>
          <h1>
            #{player.jersey} {player.first_name} {player.last_name}
          </h1>
          <p className="muted">
            {player.team}
            {player.position ? ` · ${player.position}` : ''}
          </p>
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
    </section>
  )
}
