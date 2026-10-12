import { useState } from 'react'
import { ordinal } from '../format'
import MomentList from './MomentList'

// One KPI on the card detail page. Clicking it toggles the plain-language explanation and,
// where the number can be traced to single match events, the events behind it.
export default function AttributeRow({ attr, moments, onPlay }) {
  const [open, setOpen] = useState(false)

  return (
    <li className="attribute">
      <button className="attribute-head" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span className="attribute-label">{attr.label}</span>
        <span className="attribute-value">
          {attr.display_value}
          {attr.unit && <small> {attr.unit}</small>}
        </span>
        <span className="attribute-toggle">{open ? '−' : 'ⓘ'}</span>
      </button>
      {attr.match_rank && (
        <p className="muted small">
          {ordinal(attr.match_rank)} of {attr.players_in_match} {attr.rank_pool} in this match
          {attr.detail ? ` · ${attr.detail}` : ''}
          {moments && <EventCount moments={moments} />}
        </p>
      )}
      {open && (
        <div className="attribute-explainer">
          <p>{attr.definition}</p>
          <p className="muted small">
            {attr.higher_is_better ? 'Higher is better.' : 'Lower is better.'} Official definition:{' '}
            <em>{attr.source_definition}</em>
          </p>
          {moments && (
            <div className="attribute-events">
              <h3>Behind this number</h3>
              <MomentList moments={moments} onPlay={onPlay} limit={5} />
            </div>
          )}
        </div>
      )}
    </li>
  )
}

function EventCount({ moments }) {
  const onVideo = moments.filter((m) => m.clip || m.broadcast).length
  if (moments.length === 0) return null
  return (
    <span>
      {' '}
      · {moments.length} {moments.length === 1 ? 'event' : 'events'}
      {onVideo > 0 && <span className="on-video"> · ▶ {onVideo} on video</span>}
    </span>
  )
}
