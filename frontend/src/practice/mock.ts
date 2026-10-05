import type { MockRoundInput, RoundType } from '../api/types'

export const ROUND_TYPES: RoundType[] = ['DSA', 'CS', 'LLD', 'SYSTEM_DESIGN', 'BEHAVIORAL', 'PROJECT_DEEP_DIVE']
/** Which skill components a round type may score (server-validated; used here only to filter the picker). */
export const ROUND_COMPONENTS: Record<RoundType, string[]> = {
  DSA: ['dsa', 'coding'], CS: ['cs'], LLD: ['lld'], SYSTEM_DESIGN: ['system_design'], BEHAVIORAL: ['behavioral'],
  PROJECT_DEEP_DIVE: ['project'],
}

export function emptyRound(round_type: RoundType = 'DSA'): MockRoundInput {
  return { round_type, duration_minutes: 45, round_score: 70, skills: [] }
}

export function mockErrors(rounds: MockRoundInput[]): string[] {
  const errors: string[] = []
  if (!rounds.length) errors.push('Add at least one round.')
  rounds.forEach((r, i) => {
    if (!Number.isInteger(r.round_score) || r.round_score < 0 || r.round_score > 100) errors.push(`Round ${i + 1}: score 0–100.`)
    if (!Number.isInteger(r.duration_minutes) || r.duration_minutes < 1) errors.push(`Round ${i + 1}: duration ≥ 1 min.`)
    const keys = r.skills.map((s) => s.skill)
    if (new Set(keys).size !== keys.length) errors.push(`Round ${i + 1}: a skill is listed twice.`)
  })
  return errors
}
