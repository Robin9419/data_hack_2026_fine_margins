import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import AttributeRow from '../components/AttributeRow'
import PlayerPhoto from '../components/PlayerPhoto'
import VideoSlot from '../components/VideoSlot'
import { formatMatchDate, scoreline } from '../format'

export default function CardDetail() {
  const { id } = useParams()
  const [card, setCard] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
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
          <AttributeRow key={attr.metric_id} attr={attr} />
        ))}
      </ul>

      <p className="explanation">{card.explanation}</p>

      <h2>Highlight</h2>
      <VideoSlot video={card.video} />

      <p className="muted small">
        Source: {card.source} · Edition: {card.edition === 'stadium' ? '🏟 Stadium' : 'Standard'}
      </p>
    </section>
  )
}
