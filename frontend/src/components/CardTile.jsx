import { Link } from 'react-router-dom'

export default function CardTile({ card, isNew }) {
  if (!card.owned) {
    return (
      <div className="card-tile locked" aria-label="Locked card">
        <div className="card-lock">🔒</div>
        <p className="card-title">{card.title}</p>
        <p className="muted small">{card.player.team}</p>
        <p className="muted small">Not collected yet</p>
      </div>
    )
  }

  const { player } = card
  return (
    <Link to={`/cards/${card.id}`} className="card-tile">
      {isNew && <span className="new-tag">NEW</span>}
      {card.achievement && <span className="badge">{card.achievement.badge}</span>}
      <div className="card-photo">#{player.jersey}</div>
      <p className="card-name">
        {player.first_name} {player.last_name}
      </p>
      <p className="card-title">{card.title}</p>
      <p className="muted small">{player.team}</p>
      <ul className="card-stats">
        {card.attributes.map((a) => (
          <li key={a.metric_id}>
            <strong>
              {a.display_value}
              {a.unit === '%' ? '%' : ''}
            </strong>
            <span>{a.label}</span>
          </li>
        ))}
      </ul>
    </Link>
  )
}
