import CardFace from './CardFace'

const SPARKS = 16

// Full-screen "card unlocked" moment: dimmed backdrop, light burst, the card flips in and
// sparks fly out. Stadium editions get gold confetti and a foil card (see CardFace).
// result: 'new' (first time owned) or 'upgraded' (home edition became stadium edition).
export default function CardUnlock({ card, result, points, onContinue, continueLabel = 'Continue' }) {
  const stadium = card.edition === 'stadium'
  const headline = result === 'upgraded' ? 'Card upgraded!' : 'New card unlocked!'

  return (
    <div className={`unlock ${stadium ? 'stadium' : ''}`} role="dialog" aria-modal="true" aria-label={headline}>
      <div className="unlock-burst" aria-hidden="true" />
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
      <p className="unlock-points">+{points} pts{stadium ? ' · Stadium bonus' : ''}</p>
      <button type="button" className="pack-button" onClick={onContinue}>
        {continueLabel}
      </button>
    </div>
  )
}
