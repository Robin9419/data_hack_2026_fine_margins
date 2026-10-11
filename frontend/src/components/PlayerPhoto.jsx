import { useState } from 'react'

// Player portrait. Falls back to the jersey number if there is no image or it fails to load.
export default function PlayerPhoto({ player, className = 'card-art' }) {
  const [failed, setFailed] = useState(false)
  const showImage = player.image_url && !failed

  return (
    <div className={className}>
      {showImage ? (
        <img
          src={player.image_url}
          alt={`${player.first_name} ${player.last_name}`}
          referrerPolicy="no-referrer"
          loading="lazy"
          onError={() => setFailed(true)}
        />
      ) : (
        <span>#{player.jersey}</span>
      )}
    </div>
  )
}
