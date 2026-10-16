// Nationality as shown on the card: flag image (flagcdn.com) and the three-letter code used as its alt text.
const NATIONS = {
  Switzerland: { iso: 'ch', code: 'SUI' },
  Sweden: { iso: 'se', code: 'SWE' },
  Czechia: { iso: 'cz', code: 'CZE' },
  Canada: { iso: 'ca', code: 'CAN' },
  Slovakia: { iso: 'sk', code: 'SVK' },
  USA: { iso: 'us', code: 'USA' },
}

export const nationOf = (name) => (name ? NATIONS[name] ?? null : null)
