import { useState } from 'react'

// Player portrait. Falls back to the jersey number (a star for a legend without one) if there is no image or it fails
// to load.
export default function PlayerPhoto({ player, className = 'card-art' }) {
  const [failed, setFailed] = useState(false)
  const [square, setSquare] = useState(false)
  const showImage = player.image_url && !failed

  return (
    <div className={className} style={showImage ? { '--photo': `url("${player.image_url}")` } : undefined}>
      {showImage ? (
        <img
          className={square ? 'square' : undefined}
          src={player.image_url}
          alt={`${player.first_name} ${player.last_name}`}
          referrerPolicy="no-referrer"
          loading="lazy"
          onLoad={(e) => setSquare(Math.abs(e.currentTarget.naturalWidth / e.currentTarget.naturalHeight - 1) < 0.08)}
          onError={() => setFailed(true)}
        />
      ) : (
        <span>{player.jersey ? `#${player.jersey}` : '★'}</span>
      )}
    </div>
  )
}
