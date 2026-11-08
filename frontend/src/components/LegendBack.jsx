import CardIcon from './CardIcon'
import { LEGEND_STYLE } from '../legend'
import LegendFrame from './LegendFrame'

// A compact archive record; the legend profile retains the complete biography and sources.
export default function LegendBack({ card }) {
  const { player, legend = {} } = card
  const facts = [['Position', player.position], ['Nationality', legend.nationality]]
    .filter(([, value]) => value)
  const cupHonours = legend.spengler_cup ?? []
  const honours = (cupHonours.length ? cupHonours : legend.honours ?? []).slice(0, 2)

  return (
    <span className="spotlight-back card-face legend legend-retro legend-back legend-variant-midnight" style={LEGEND_STYLE}>
      <span className="legend-paper">
        <span className="legend-back-sheet">
          <span className="legend-back-label"><CardIcon name="star" />Legend archive</span>
          <span className="legend-back-heading" style={{ '--nlen': player.last_name.length }}>
            <span>{player.jersey != null && `#${player.jersey} · `}{player.first_name}</span>
            <strong>{player.last_name}</strong>
            <small>{player.team}</small>
          </span>
          <span className="legend-back-facts">
            {facts.map(([label, value]) => (
              <span className="legend-back-row" key={label}>
                <span>{label}</span><strong>{value}</strong>
              </span>
            ))}
          </span>
          {legend.summary && (
            <span className="legend-back-section">
              <strong className="legend-back-subtitle">The story</strong>
              <span className="legend-back-summary">{legend.summary}</span>
            </span>
          )}
          {honours.length > 0 && (
            <span className="legend-back-section">
              <strong className="legend-back-subtitle">{cupHonours.length ? 'Spengler Cup record' : 'Career honours'}</strong>
              {honours.map((honour, index) => (
                <span className="legend-back-honour" key={`${index}-${honour}`}><CardIcon name="star" /><span>{honour}</span></span>
              ))}
            </span>
          )}
        </span>
        <span className="legend-back-footnote">Full record in the legend profile</span>
        <span className="legend-retro-footer"><span>Spengler Cup</span><CardIcon name="star" /><span>Club legends</span></span>
      </span>
      <LegendFrame glint={false} />
    </span>
  )
}
