import { Link } from 'react-router-dom'
import CardFace from './CardFace'

// onOpen: when given, an owned special card opens in place (the spotlight) instead of going to its page.
export default function CardTile({ card, isNew, onOpen }) {
  if (!card.owned) {
    return (
      <div className="card-tile locked" aria-label="Locked card. Answer trivia questions to unlock it.">
        <CardFace card={card} state="locked" />
        <span className="lock-chip">🔒 Locked</span>
      </div>
    )
  }

  if (onOpen && card.type === 'special') {
    return (
      <button type="button" className="card-tile" onClick={() => onOpen(card)}>
        {isNew && <span className="new-tag">NEW</span>}
        <CardFace card={card} />
      </button>
    )
  }

  return (
    <Link to={`/cards/${card.id}`} className="card-tile">
      {isNew && <span className="new-tag">NEW</span>}
      <CardFace card={card} />
    </Link>
  )
}
