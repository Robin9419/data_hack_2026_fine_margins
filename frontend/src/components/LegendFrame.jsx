import { useId } from 'react'

// The legend frame: filigree scrollwork on a gold double line.
// Drawn on the 100 x 140 card grid (5:7, so 1 unit = 1cqw on both axes). Every line follows the
// shield outline; ornaments stay in the margin band or over the photo, clear of the header, name and footer.

const n = (v) => +v.toFixed(2)
// The shield outline inset by d units: the straight edges move inward by d, the corners follow.
const shield = (d) =>
  `M${n(13 + 0.37 * d)} ${n(d)}H${n(87 - 0.37 * d)}L${n(100 - d)} ${n(11 + 0.46 * d)}V${n(121 - 0.2 * d)}` +
  `Q${n(100 - d)} ${n(127 - 0.75 * d)} ${n(92 - 0.25 * d)} ${n(129 - 0.97 * d)}L${n(56 - 0.1 * d)} ${n(138 - 1.03 * d)}` +
  `Q50 ${n(140 - 1.1 * d)} ${n(44 + 0.1 * d)} ${n(138 - 1.03 * d)}L${n(8 + 0.25 * d)} ${n(129 - 0.97 * d)}` +
  `Q${n(d)} ${n(127 - 0.75 * d)} ${n(d)} ${n(121 - 0.2 * d)}V${n(11 + 0.46 * d)}Z`


// Draws its children on the left half and mirrors them onto the right.
function Mirror({ children }) {
  return (
    <>
      <g>{children}</g>
      <g transform="translate(100 0) scale(-1 1)">{children}</g>
    </>
  )
}

// Filigree: twin lines with scrollwork curling in from the sides and a swag hanging from the top.
function Filigree({ gold }) {
  return (
    <>
      <path d={shield(0)} stroke={gold} strokeWidth="2" />
      <path d={shield(3)} stroke={gold} strokeWidth="0.4" />
      <path d="M36 3C43 3 45 7.2 50 7.2C55 7.2 57 3 64 3" stroke={gold} strokeWidth="0.6" />
      <circle cx="50" cy="9" r="0.8" fill={gold} />
      <Mirror>
        <g stroke={gold} strokeWidth="0.6" strokeLinecap="round">
          <path d="M3 33C10 35 11.5 42 7 44C4 45.2 3.6 42.2 5.6 41.6" />
          <path d="M3 57C10 55 11.5 48 7 46C4 44.8 3.6 47.8 5.6 48.4" />
          <path d="M3 41C5 43 5 47 3 49" />
          <path d="M3 18C6.5 19 7 22.5 5 23.5" />
        </g>
        <circle cx="10.2" cy="45" r="0.9" fill={gold} />
        <circle cx="12.4" cy="45" r="0.5" fill={gold} />
      </Mirror>
    </>
  )
}

export default function LegendFrame({ glint = true }) {
  const id = useId().replace(/:/g, '')
  const gold = `url(#${id}-gold)`
  return (
    <svg className="legend-outline" viewBox="0 0 100 140" preserveAspectRatio="none" fill="none" aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id={`${id}-gold`} x1="0" y1="0" x2="100" y2="140" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#fff3cf" />
          <stop offset="0.22" stopColor="#d5bd8d" />
          <stop offset="0.45" stopColor="#8f7140" />
          <stop offset="0.6" stopColor="#f2deaa" />
          <stop offset="0.8" stopColor="#b08f52" />
          <stop offset="1" stopColor="#ecd7a0" />
        </linearGradient>
      </defs>
      <g strokeLinejoin="round">
        <Filigree gold={gold} />
      </g>
      {glint && <path className="legend-glint" d={shield(0)} pathLength="100" stroke="#fffaf0" strokeWidth="1.6" strokeLinecap="round" />}
    </svg>
  )
}
