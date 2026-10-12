// Video highlight for a card. `video` is the card's own highlight: a clip cut from the arena
// recording ({ url, poster }), a stretch of the YouTube broadcast highlights ({ youtube_id,
// start, end }), a self-hosted file set on the card in cards.json, or null. `playing` is the
// clip picked from a game event; it replaces the highlight until another one is picked.
// Nothing autoplays until the user presses play.
export default function VideoSlot({ video, playing, onPlay, sources = [] }) {
  const clip = playing || video
  if (!clip) {
    return (
      <div className="video-placeholder">
        <span className="play">▶</span>
        <p>Highlight unavailable in this demo</p>
      </div>
    )
  }

  const source = sources.find((s) => s.id === clip.video_id)
  const caption = playing
    ? playing.label
    : video.scope === 'game'
      ? video.description
      : `Highlight from this performance${video.description ? `: ${video.description}` : '.'}`

  let player
  if (clip.url) {
    player = (
      <div className="video-frame">
        <video
          key={playing?.nonce ?? 'card'}
          src={clip.url}
          poster={clip.poster}
          controls
          playsInline
          autoPlay={Boolean(playing)}
          preload={playing ? 'auto' : 'none'}
        />
      </div>
    )
  } else if (playing) {
    player = (
      <div className="video-frame">
        <iframe
          key={playing.nonce}
          src={embedUrl(playing)}
          title={caption}
          allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
          referrerPolicy="strict-origin-when-cross-origin"
          allowFullScreen
        />
      </div>
    )
  } else {
    player = (
      <button className="video-frame video-poster" onClick={() => onPlay(video, caption)}>
        <img src={video.poster} alt="" />
        <span className="play">▶</span>
        {video.end != null && <span className="video-length">{video.end - video.start} s</span>}
      </button>
    )
  }

  return (
    <figure className="video">
      {player}
      <figcaption>
        {caption}
        {source && <SourceLine clip={clip} source={source} />}
      </figcaption>
    </figure>
  )
}

function SourceLine({ clip, source }) {
  if (!source.youtube_id) return <span className="muted small video-source">Video: {source.title}</span>
  return (
    <span className="muted small video-source">
      Video:{' '}
      <a href={`${source.url}&t=${clip.start}s`} target="_blank" rel="noreferrer">
        {source.channel}
      </a>
      , official YouTube channel
      {clip.end != null ? ` · clip ${clipTime(clip.start)}–${clipTime(clip.end)} of the highlights` : ''}
    </span>
  )
}

// Started by a click, so autoplay here is the user's own play action.
const embedUrl = (clip) => {
  const params = new URLSearchParams({ autoplay: '1', rel: '0', playsinline: '1', start: String(clip.start) })
  if (clip.end != null) params.set('end', String(clip.end))
  return `https://www.youtube-nocookie.com/embed/${clip.youtube_id}?${params}`
}

const clipTime = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
