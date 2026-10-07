import type { Readiness, SkillWithState } from '../api/types'
import { isCommunicationSkill } from './communication'
import { ACTIONABLE_GAP_STATUSES, STAGE_LABEL, type PrepareCategory } from './language'

/** Per-area summary for the Prepare pages. Reads server values only; sorts by the engine's own rank. */
export interface CategorySummary {
  score: number | null
  target: number | null
  assessedPct: number | null
  /** The skill the gap engine ranks highest within this area (actionable statuses only). */
  topGap: SkillWithState | null
  /** Actionable gaps in this area, engine rank order. */
  gaps: SkillWithState[]
  nextLabel: string | null
}

export function skillsInCategory(category: PrepareCategory, skills: readonly SkillWithState[]): SkillWithState[] {
  return skills.filter(
    (s) => (category.components as readonly string[]).includes(s.component) && !isCommunicationSkill(s.key),
  )
}

export function summarizeCategory(
  category: PrepareCategory,
  skills: readonly SkillWithState[],
  readiness: Readiness | null,
): CategorySummary {
  const component = readiness?.components.find((c) => c.key === category.primary) ?? null
  const gaps = skillsInCategory(category, skills)
    .filter((s) => s.gap && (ACTIONABLE_GAP_STATUSES as readonly string[]).includes(s.gap.status))
    .sort((a, b) => a.gap!.rank - b.gap!.rank)
  const topGap = gaps[0] ?? null
  const stage = topGap?.gap?.focus_stage ?? null
  return {
    score: component?.score ?? null,
    target: component?.gate ?? null,
    assessedPct: component?.assessed_pct ?? null,
    topGap,
    gaps,
    nextLabel: topGap ? `${stage ? (STAGE_LABEL[stage] ?? stage) : 'Practice'} · ${topGap.name}` : null,
  }
}
