import { prettyKey } from './format'

/**
 * Human sentences for the gap engine's reason codes (GAP_ENGINE §9). The codes come from the server; this table
 * only words them. It never decides which reasons apply and never invents a number.
 */
const PHRASE: Record<string, string> = {
  UNASSESSED: "We haven't measured this yet.",
  DECLARED_UNKNOWN: 'You told us this is new to you.',
  LARGE_GAP: 'It is a long way from your target.',
  BELOW_FLOOR: 'It is below the minimum level for your target role.',
  HIGH_IMPORTANCE: 'It is core to your target role.',
  LOW_CONFIDENCE: "There isn't enough evidence yet to be sure.",
  REPEATED_FAILURE: 'Recent attempts keep failing.',
  MOCK_WEAKNESS: 'It showed up as a weakness in a mock.',
  GATE_FAILING: 'Its area is below the level needed for the next readiness step.',
  RETENTION_RISK: "It's been a while, so retention is at risk.",
  DECAYED: 'Your recall has slipped since your best result.',
  PATTERN_MISIDENTIFIED: "You've been picking the wrong approach.",
  SPEED_BELOW_TARGET: 'You solve it, but slower than interview pace.',
  OVERCONFIDENT: 'Your confidence has run ahead of your results.',
  UNDERCONFIDENT: 'You do better than you expect. Trust it.',
  STUDIED_NOT_TESTED: "You've studied it but haven't tested yourself yet.",
  PREREQUISITE_BLOCKED: 'A prerequisite needs work first.',
  OVERDUE_REVISION: 'A review is overdue.',
  OVER_TARGET: 'Already at target. Maintain it only.',
  PARKED_DEADLINE: 'Parked until after your interview date.',
  NOT_FEASIBLE: 'Out of reach in the time you have left.',
}

/** The most useful reasons first (what the user can act on), skipping the ones that restate the score. */
const PRIORITY = [
  'REPEATED_FAILURE', 'PATTERN_MISIDENTIFIED', 'MOCK_WEAKNESS', 'OVERCONFIDENT', 'SPEED_BELOW_TARGET', 'DECAYED',
  'RETENTION_RISK', 'OVERDUE_REVISION', 'STUDIED_NOT_TESTED', 'PREREQUISITE_BLOCKED', 'BELOW_FLOOR', 'GATE_FAILING',
  'LARGE_GAP', 'HIGH_IMPORTANCE', 'LOW_CONFIDENCE', 'UNDERCONFIDENT', 'DECLARED_UNKNOWN', 'UNASSESSED',
]

export function reasonPhrase(code: string, nameOf: (key: string) => string = prettyKey): string | null {
  if (code.startsWith('UNLOCKS:')) return `Unlocks ${nameOf(code.slice('UNLOCKS:'.length))}.`
  return PHRASE[code] ?? null
}

export function reasonPhrases(codes: readonly string[], nameOf: (key: string) => string, limit = 2): string[] {
  const known = codes.filter((c) => c.startsWith('UNLOCKS:') || c in PHRASE)
  const rank = (c: string) => {
    const i = PRIORITY.indexOf(c)
    return i === -1 ? PRIORITY.length : i
  }
  return [...known]
    .sort((a, b) => rank(a) - rank(b))
    .slice(0, limit)
    .map((c) => reasonPhrase(c, nameOf))
    .filter((p): p is string => p !== null)
}
