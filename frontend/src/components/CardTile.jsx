import { Link } from 'react-router-dom'
import CardFace from './CardFace'

export default function CardTile({ card, isNew }) {
  if (!card.owned) {
    return (
      <div className="card-tile locked" aria-label="Locked card. Answer trivia questions to unlock it.">
        <CardFace card={card} state="locked" />
        <span className="lock-chip">🔒 Locked</span>
      </div>
    )
  }

  return (
    <Link to={`/cards/${card.id}`} className="card-tile">
      {isNew && <span className="new-tag">NEW</span>}
      <CardFace card={card} />
    </Link>
  )
}
