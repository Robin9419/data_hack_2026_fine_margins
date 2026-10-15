import { Link } from 'react-router-dom'
import CardFace from './CardFace'

// onOpen: when given, an owned special card opens in place (the spotlight) instead of going to its page.
// club: the club's progress (from progress.clubs). Shown on hover or focus over a locked legend.
export default function CardTile({ card, isNew, onOpen, club }) {
  if (!card.owned && card.type === 'legend') {
    return (
      <div className="card-tile locked" tabIndex={0} aria-label={`Locked ${card.player.team} legend. Collect the club's cards to unlock it.`}>
        <CardFace card={card} state="locked" />
        {club && <ClubProgress club={club} />}
      </div>
    )
  }

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
      {card.copies > 1 && <span className="copies-tag" title={`You have ${card.copies} copies`}>×{card.copies}</span>}
      <CardFace card={card} />
    </Link>
  )
}

// Each club's legends are earned at 50%, 75% and 100% of its cards. The bar marks those steps.
function ClubProgress({ club }) {
  return (
    <div className="club-legend">
      <div className="club-legend-head">
        <strong>{club.team}</strong>
        <span className="club-legend-stars" aria-label={`${club.legends_owned} of ${club.legends_total} legends`}>
          {Array.from({ length: club.legends_total }, (_, i) => (
            <span key={i} className={i < club.legends_owned ? 'on' : ''} aria-hidden="true">
              ★
            </span>
          ))}
        </span>
      </div>
      <div className="club-legend-track" role="progressbar" aria-valuemin={0} aria-valuemax={club.total} aria-valuenow={club.owned}>
        <div className="club-legend-fill" style={{ width: `${(club.owned / club.total) * 100}%` }} />
        {club.thresholds.map((n) => (
          <span key={n} className={`club-legend-step ${club.owned >= n ? 'reached' : ''}`} style={{ left: `${(n / club.total) * 100}%` }} />
        ))}
      </div>
      <span className="muted small">
        {club.owned} / {club.total} cards ·{' '}
        {club.next_at ? `next legend at ${club.next_at}` : 'all legends earned'}
      </span>
    </div>
  )
}
