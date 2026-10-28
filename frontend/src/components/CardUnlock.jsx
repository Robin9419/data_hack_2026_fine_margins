import { createPortal } from 'react-dom'
import CardFace from './CardFace'

const SPARKS = 16

// "Card unlocked" moment between the header and the timeline: dimmed panel, light burst, the card flips in and
// sparks fly out. Stadium editions get gold confetti and a foil card (see CardFace).
// result: 'new' (first time owned), 'upgraded' (home edition became stadium edition) or 'legend' (a club legend earned
// by collecting the club's cards; points is then null).
export default function CardUnlock({ card, result, points, onContinue, continueLabel = 'Continue' }) {
  const stadium = card.edition === 'stadium'
  const legend = result === 'legend'
  const headline = legend ? 'Club legend earned!' : result === 'upgraded' ? 'Card upgraded!' : 'New card unlocked!'

  return createPortal(
    <div className={`unlock ${stadium || legend ? 'stadium' : ''} ${legend ? 'legend' : ''}`} role="dialog" aria-modal="true" aria-label={headline}>
      <div className="unlock-burst" aria-hidden="true" />
      <div className="unlock-body">
        <h2 className="unlock-title">{headline}</h2>
        <div className="unlock-card">
          <div className="unlock-sparks" aria-hidden="true">
            {Array.from({ length: SPARKS }, (_, i) => (
              <span key={i} style={{ '--a': `${(360 / SPARKS) * i}deg`, '--d': `${i % 2 ? 150 : 210}px` }} />
            ))}
          </div>
          <div className="unlock-flip">
            <CardFace card={card} />
          </div>
        </div>
        <p className="unlock-points">
          {legend ? `You collected enough ${card.player.team} cards` : `+${points} pts${stadium ? ' · Stadium bonus' : ''}`}
        </p>
        <button type="button" className="pack-button" onClick={onContinue}>
          {continueLabel}
        </button>
      </div>
    </div>,
    document.body,
  )
}
