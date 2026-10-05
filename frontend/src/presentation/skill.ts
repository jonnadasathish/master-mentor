import type { EvidenceRow, GapDetail } from '../api/types'
import { COMPONENT_LABEL, OBSERVATION_LABEL, SOURCE_LABEL } from './language'
import { reasonPhrases } from './reasons'

/** Plain-language explanation of a weak skill, built only from numbers and codes the server returned. */
export function whyWeak(
  gap: Pick<GapDetail, 'component' | 'metrics' | 'reason_codes'>,
  nameOf: (key: string) => string,
): string[] {
  const m = gap.metrics
  const lines: string[] = []
  if (m.n_fail_last5 > 0) lines.push(`${m.n_fail_last5} of your last 5 attempts failed.`)
  if (m.pattern_misses_last4 > 0) lines.push(`You missed the pattern in ${m.pattern_misses_last4} of your last 4 attempts.`)
  if (m.speed_median_ratio_bp !== null && m.speed_median_ratio_bp > 12500) {
    lines.push(`You usually take ${Math.round(m.speed_median_ratio_bp / 100)}% of the time limit.`)
  }
  if (m.depth_mean_last3 !== null && m.depth_mean_last3 < 60) lines.push(`Your recent explanations average ${Math.round(m.depth_mean_last3)} out of 100.`)
  if (m.communication_mean_last3 !== null && m.communication_mean_last3 < 60) {
    lines.push(`Your recent communication averages ${Math.round(m.communication_mean_last3)} out of 100.`)
  }
  if (m.overconfident_rows > 0) lines.push(`In ${m.overconfident_rows} recent attempts you felt more confident than your result.`)
  // Only worth saying when the gap is long enough to matter.
  if (m.days_since_last_practice !== null && m.days_since_last_practice >= 7) {
    lines.push(`You last practised this ${m.days_since_last_practice} days ago.`)
  }
  const area = COMPONENT_LABEL[gap.component]
  const areaLine = area && m.component_score < m.component_gate
  if (areaLine) lines.push(`${area} overall is at ${m.component_score}; it needs ${m.component_gate}.`)
  // A reason code that a metric above already spelled out with numbers is not repeated.
  const covered = new Set<string>([
    ...(m.n_fail_last5 > 0 ? ['REPEATED_FAILURE'] : []),
    ...(m.pattern_misses_last4 > 0 ? ['PATTERN_MISIDENTIFIED'] : []),
    ...(m.overconfident_rows > 0 ? ['OVERCONFIDENT'] : []),
    ...(m.speed_median_ratio_bp !== null && m.speed_median_ratio_bp > 12500 ? ['SPEED_BELOW_TARGET'] : []),
    ...(areaLine ? ['GATE_FAILING'] : []),
  ])
  const remaining = gap.reason_codes.filter((c) => !covered.has(c))
  for (const phrase of reasonPhrases(remaining, nameOf, 3)) {
    if (!lines.includes(phrase)) lines.push(phrase)
  }
  return lines
}

/** Short headline for an evidence row in the timeline. */
export function evidenceTitle(row: EvidenceRow): string {
  if (row.source_type === 'ATTEMPT') return 'Practice attempt'
  if (row.source_type === 'MOCK_ROUND') return 'Mock interview'
  if (row.kind === 'SELF_ASSESSMENT') return 'Your self-rating'
  const label = row.kind ? OBSERVATION_LABEL[row.kind] : null
  if (label) return label.replace(/^an? /, '').replace(/^./, (c) => c.toUpperCase())
  return SOURCE_LABEL[row.source_type] ?? 'Observation'
}

export const FAMILIARITY_LABEL: Record<string, string> = { NONE: 'New to you', SOME: 'Some familiarity', SOLID: 'Solid' }

export function evidenceDetail(row: EvidenceRow): string {
  if (row.kind === 'SELF_ASSESSMENT' && row.familiarity) return FAMILIARITY_LABEL[row.familiarity] ?? row.familiarity
  if (!row.is_scoring) return 'Not scored'
  const parts: string[] = []
  if (row.outcome_points !== null) parts.push(`Scored ${row.outcome_points}`)
  if (row.timed) parts.push(row.within_limit === false ? 'over the time limit' : 'timed')
  if (row.is_weakness) parts.push('flagged as a weakness')
  return parts.join(' · ')
}
