import { useState } from 'react'
import { ordinal } from '../format'

// One KPI on the card detail page. Clicking it toggles the plain-language explanation.
export default function AttributeRow({ attr }) {
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
        </p>
      )}
      {open && (
        <div className="attribute-explainer">
          <p>{attr.definition}</p>
          <p className="muted small">
            {attr.higher_is_better ? 'Higher is better.' : 'Lower is better.'} Official definition:{' '}
            <em>{attr.source_definition}</em>
          </p>
        </div>
      )}
    </li>
  )
}
