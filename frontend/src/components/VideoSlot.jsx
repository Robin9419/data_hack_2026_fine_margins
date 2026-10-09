// Video highlight for a card. `video` is null until an authorized clip is added to
// backend/content/cards.json as { "url": ..., "poster": ..., "description": ... }.
export default function VideoSlot({ video }) {
  if (!video) {
    return (
      <div className="video-placeholder">
        <span className="play">▶</span>
        <p>Highlight unavailable in this demo</p>
      </div>
    )
  }

  return (
    <figure className="video">
      <video controls preload="none" poster={video.poster} src={video.url} />
      <figcaption>
        Highlight from this performance{video.description ? `: ${video.description}` : '.'}
      </figcaption>
    </figure>
  )
}
