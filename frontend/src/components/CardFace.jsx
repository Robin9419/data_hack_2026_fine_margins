import { teamClass } from '../format'
import PlayerPhoto from './PlayerPhoto'

// Front of a card: photo, archetype (or 'Base' for a base card), name, position and team. Nothing else.
// state: 'owned' (full colour), 'locked' (gallery: grayed out photo only, no info) or 'hidden'
// (a mystery card in a pack: no photo, name or archetype, so nothing leaks before it is revealed).
// A card with edition 'stadium' gets the foil design. A legend has its own black-and-gold design with a black and white
// photo; a locked legend shows only its club.
export default function CardFace({ card, state = 'owned' }) {
  if (card.type === 'legend' && state !== 'hidden') return <LegendFace card={card} locked={state === 'locked'} />

  if (state === 'locked') {
    return (
      <div className={`card-face ${teamClass(card.player.team)} locked`}>
        <PlayerPhoto player={card.player} className="card-art" />
      </div>
    )
  }

  if (state !== 'owned') {
    return (
      <div className={`card-face mystery ${state}`}>
        <span className="mystery-mark">?</span>
        <div className="card-info">
          <p className="card-archetype">? ? ?</p>
          <p className="card-name">Mystery player</p>
        </div>
      </div>
    )
  }

  const { player } = card
  const stadium = card.edition === 'stadium'
  const base = card.type === 'base'
  return (
    <div className={`card-face ${teamClass(player.team)} ${stadium ? 'edition-stadium' : ''} ${base ? 'base' : ''} ${state}`}>
      <PlayerPhoto player={player} className="card-art" />
      {stadium && <span className="edition-badge">🏟 Stadium</span>}
      <div className="card-info">
        <p className="card-archetype">{base ? 'Base' : card.title}</p>
        <p className="card-name">
          <span className="card-first">{player.first_name}</span>
          {player.last_name}
        </p>
        <p className="card-meta">
          {player.position ? `${player.position} · ` : ''}
          {player.team}
        </p>
      </div>
    </div>
  )
}

function LegendFace({ card, locked }) {
  const { player } = card
  if (locked) {
    return (
      <div className="card-face legend locked-legend">
        <span className="legend-star" aria-hidden="true">★</span>
        <div className="card-info">
          <p className="card-archetype">Club legend</p>
          <p className="card-name">{player.team}</p>
          <p className="card-meta">Collect the club's cards to unlock</p>
        </div>
      </div>
    )
  }
  return (
    <div className="card-face legend">
      <PlayerPhoto player={player} className="card-art" />
      <span className="legend-ribbon">★ Legend</span>
      <div className="card-info">
        <p className="card-archetype">Club legend</p>
        <p className="card-name">
          <span className="card-first">{player.first_name}</span>
          {player.last_name}
        </p>
        <p className="card-meta">{player.team}</p>
      </div>
    </div>
  )
}
