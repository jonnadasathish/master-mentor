/**
 * Wording clean-up for backend-written sentences. Pure string work: it swaps identifiers for names and technical
 * criteria for plain phrases. It never changes a number and never decides anything.
 */

/** "outcome_points >= 70 (L2 evidence)" -> "a score of 70 or more". */
export function tidyCriteria(text: string): string {
  return text
    .replace(/\s*\(L\d evidence\)/gi, '')
    .replace(/\bfollowup_points\s*>=\s*(\d+)/gi, 'a follow-up score of $1 or more')
    .replace(/\boutcome_points\s*>=\s*(\d+)(\s+per skill)?/gi, (_m, n: string, per?: string) => `a score of ${n} or more${per ? ' on each skill' : ''}`)
    .replace(/\b(\w+)\.outcome_points\s*>=\s*(\d+)/gi, 'a score of $2 or more')
    .replace(/\s+and\s+/gi, ' and ')
    .replace(/^./, (c) => c.toUpperCase())
}

/** Replace skill keys and baseline item keys inside a sentence with their human names (longest key first). */
export function humaniseKeys(
  text: string,
  names: ReadonlyMap<string, string> | readonly (readonly [string, string])[],
): string {
  const pairs = [...(names instanceof Map ? names.entries() : names)].sort((a, b) => b[0].length - a[0].length)
  return pairs.reduce((out, [key, name]) => (out.includes(key) ? out.split(key).join(name) : out), text)
}
