// Follow the actual shield outline: an inset rectangular panel cannot frame its sloping corners.
export default function LegendFrame() {
  return (
    <svg className="legend-outline" viewBox="0 0 100 140" preserveAspectRatio="none" fill="none" aria-hidden="true" focusable="false">
      <path d="M13 0H87L100 11V121Q100 127 92 129L56 138Q50 140 44 138L8 129Q0 127 0 121V11Z" stroke="currentColor" strokeWidth="2.5" strokeLinejoin="round" />
    </svg>
  )
}
