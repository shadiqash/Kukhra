import NepaliDate from 'nepali-date-converter'

const BS_MONTHS = [
  'Baisakh', 'Jestha', 'Ashadh', 'Shrawan', 'Bhadra', 'Ashwin',
  'Kartik', 'Mangsir', 'Poush', 'Magh', 'Falgun', 'Chaitra',
]

/**
 * Convert an AD date string or Date to a BS date string.
 * @param {string|Date} value - ISO date string or Date object
 * @param {'numeric'|'short'|'long'} [style='numeric'] - output format
 *   'numeric' → "2083-03-09"
 *   'short'   → "09 Asa 2083"
 *   'long'    → "09 Ashadh 2083"
 * @returns {string}
 */
export function formatBSDate(value, style = 'numeric') {
  if (!value) return '—'
  try {
    const ad = value instanceof Date ? value : new Date(value)
    const bs = new NepaliDate(ad)
    const y = bs.getYear()
    const m = bs.getMonth()   // 0-indexed
    const d = String(bs.getDate()).padStart(2, '0')

    if (style === 'numeric') return `${y}-${String(m + 1).padStart(2, '0')}-${d}`
    const monthName = BS_MONTHS[m] ?? ''
    if (style === 'short') return `${d} ${monthName.slice(0, 3)} ${y}`
    return `${d} ${monthName} ${y}`
  } catch {
    return '—'
  }
}
