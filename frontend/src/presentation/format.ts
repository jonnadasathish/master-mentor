/** Pure presentation helpers: formatting only, no domain logic. */

/** 95 -> "1h 35m", 60 -> "1h", 35 -> "35 min". */
export function formatMinutes(minutes: number): string {
  const m = Math.max(0, Math.round(minutes))
  if (m < 60) return `${m} min`
  const h = Math.floor(m / 60)
  const rest = m % 60
  return rest ? `${h}h ${rest}m` : `${h}h`
}

/** Bar width in percent, clamped. Presentation only (the score and target come from the server). */
export function barPercent(value: number | null | undefined, max: number | null | undefined): number {
  if (value == null || !max || max <= 0) return 0
  return Math.max(0, Math.min(100, (value / max) * 100))
}

export function greetingFor(hour: number): string {
  if (hour < 5) return 'Good evening'
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
}

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
const WEEKDAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

function parseDay(iso: string): { y: number; m: number; d: number } | null {
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number)
  return y && m && d ? { y, m, d } : null
}

/** ISO date (YYYY-MM-DD) -> "12 Oct". Built by hand so the wording never depends on the browser's locale data. */
export function shortDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const day = parseDay(iso)
  return day ? `${day.d} ${MONTHS[day.m - 1]!.slice(0, 3)}` : iso
}

/** "2026-10-05" -> "Monday, 5 October". */
export function longDate(iso: string): string {
  const day = parseDay(iso)
  if (!day) return iso
  const weekday = WEEKDAYS[new Date(Date.UTC(day.y, day.m - 1, day.d)).getUTCDay()]!
  return `${weekday}, ${day.d} ${MONTHS[day.m - 1]}`
}

export function plural(n: number, one: string, many = `${one}s`): string {
  return `${n} ${n === 1 ? one : many}`
}

/** "two_pointers.core" -> "Two pointers core" fallback when the catalog name is not loaded yet. */
export function prettyKey(key: string): string {
  const last = key.split('.').at(-1) ?? key
  const text = last.replace(/_/g, ' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}

/** "2027-06-28" -> "June 2027". */
export function monthYear(iso: string | null | undefined): string {
  if (!iso) return ''
  const day = parseDay(iso)
  return day ? `${MONTHS[day.m - 1]} ${day.y}` : iso
}

/** "38.0" -> "38", "38.5" -> "38.5" (the server sends one decimal). */
export function trimWeeks(weeks: string): string {
  return weeks.replace(/\.0$/, '')
}
