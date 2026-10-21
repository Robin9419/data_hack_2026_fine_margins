// Link to the player's public Instagram profile. Only set for players whose handle is confirmed by a reliable source.
export default function InstagramLink({ player }) {
  if (!player.instagram) return null
  return (
    <p className="instagram-link">
      <a href={`https://www.instagram.com/${player.instagram}/`} target="_blank" rel="noreferrer">
        Instagram @{player.instagram}
      </a>
    </p>
  )
}
