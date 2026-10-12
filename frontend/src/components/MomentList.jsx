import { useState } from 'react'

// What a broadcast clip shows for each kind of moment: the highlights only show goals.
const BROADCAST_LABEL = {
  goal: 'TV replay of the goal',
  assist: 'TV replay of the goal this set up',
  goal_against: 'TV replay of the goal conceded',
}

const describe = (m) => `${m.title} at ${m.clock} of the ${m.period_label}. ${m.text}`.trim()

// Single game events from the Wisehockey match events data, oldest first. Each event with
// footage gets a play button for its arena-camera clip; goals also get the TV replay.
export default function MomentList({ moments, onPlay, limit = 6 }) {
  const [showAll, setShowAll] = useState(false)
  if (moments.length === 0) return <p className="muted small">No events of this kind in the match data.</p>

  const shown = showAll ? moments : moments.slice(0, limit)
  return (
    <>
      <ol className="moments">
        {shown.map((m) => (
          <li key={m.id} className={`moment moment-${m.kind}`}>
            <span className="moment-time">
              {m.clock}
              <small>{m.period_label}</small>
            </span>
            <span className="moment-body">
              <strong>{m.title}</strong>
              {m.text && <span> · {m.text}</span>}
              {m.facts.length > 0 && <span className="moment-facts">{m.facts.join(' · ')}</span>}
            </span>
            <span className="moment-actions">
              {m.clip && (
                <button className="moment-play" onClick={() => onPlay(m.clip, describe(m))} title="Watch this moment">
                  ▶ <span>Watch</span>
                </button>
              )}
              {m.broadcast && (
                <button
                  className={m.clip ? 'moment-play secondary' : 'moment-play'}
                  onClick={() => onPlay(m.broadcast, `${BROADCAST_LABEL[m.kind]}. ${describe(m)}`)}
                  title={BROADCAST_LABEL[m.kind]}
                >
                  {m.clip ? 'TV' : <>▶ <span>{BROADCAST_LABEL[m.kind]}</span></>}
                </button>
              )}
            </span>
          </li>
        ))}
      </ol>
      {moments.length > limit && (
        <button className="link-button small" onClick={() => setShowAll(!showAll)}>
          {showAll ? 'Show fewer' : `Show all ${moments.length}`}
        </button>
      )}
    </>
  )
}
