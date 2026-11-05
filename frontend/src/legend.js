export const LEGEND_STYLE = { '--c1': '#081d24', '--c2': '#d5bd8d' }

// Era labels can contain multiple seasons, abbreviated end years and open-ended tenures.
export function legendYears(era = '') {
  const years = []
  for (const match of era.matchAll(/(\d{4})(?:\s*[–-]\s*(\d{4}|\d{2})(?!\d)|\s*([–-])(?!\d))?/g)) {
    const start = Number(match[1])
    if (match[2]) {
      let end = Number(match[2])
      if (match[2].length === 2) {
        end += Math.floor(start / 100) * 100
        if (end < start) end += 100
      }
      years.push(`${start}–${end}`)
    } else {
      years.push(`${start}${match[3] ? '–' : ''}`)
    }
  }
  return years.join(' · ')
}
