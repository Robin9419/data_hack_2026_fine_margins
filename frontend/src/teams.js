// Teams of the tournament: logo and colours used on cards and in the team picker.
// TEAMS are the teams of the card set (the 2025 Spengler Cup, same names as TEAMS in backend/app/main.py).
// TEAMS_2026 are the other clubs of the 2026 line-up: logos and names only, there are no cards for them yet.
export const TEAMS = [
  { name: 'HIFK', short: 'HIF', logo: '/logos/hifk.png', c1: '#c8102e', c2: '#ffffff' },
  { name: 'Team Canada', short: 'CAN', logo: '/logos/canada.png', c1: '#c8102e', c2: '#ffffff' },
  { name: 'HC Davos', short: 'HCD', logo: '/logos/davos.png', c1: '#0a2d6e', c2: '#ffd400' },
  { name: 'HC Sparta Praha', short: 'SPA', logo: '/logos/sparta.png', c1: '#9c1c2c', c2: '#f5c400', logoScale: 0.85 },
  { name: 'HC Fribourg-Gottéron', short: 'FRI', logo: '/logos/fribourg.png', c1: '#111111', c2: '#ffffff', logoScale: 0.85 },
  { name: 'U.S. Collegiate Selects', short: 'USA', logo: '/logos/usa.png', c1: '#13284f', c2: '#ff4d5a', logoScale: 0.85 },
]

export const TEAMS_2026 = [
  { name: 'SCL Tigers', short: 'SCL', logo: '/logos/scl.png', c1: '#111111', c2: '#f58220' },
  { name: 'Adler Mannheim', short: 'ADL', logo: '/logos/adler.png', c1: '#0b2a5b', c2: '#d6001c' },
  { name: 'Ilves Tampere', short: 'ILV', logo: '/logos/ilves.png', c1: '#111111', c2: '#f5c400' },
  { name: 'Frölunda HC', short: 'FHC', logo: '/logos/frolunda.png', c1: '#00573f', c2: '#ffffff' },
]

const FALLBACK = { short: '', logo: null, c1: '#13284f', c2: '#ff4d5a' }

export const teamOf = (name) => [...TEAMS, ...TEAMS_2026].find((t) => t.name === name) ?? { ...FALLBACK, name }

// Inline style that sets the team colours (--c1, --c2) for a card.
export const teamStyle = (name) => {
  const { c1, c2 } = teamOf(name)
  return { '--c1': c1, '--c2': c2 }
}
