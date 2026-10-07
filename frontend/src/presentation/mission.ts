import type { BatteryItem, PlanItem } from '../api/types'
import { areaLabel } from './communication'
import { COMPONENT_LABEL, OBSERVATION_LABEL, STAGE_LABEL } from './language'
import { prettyKey } from './format'
import { reasonPhrases } from './reasons'
import { tidyCriteria } from './text'

/** Wording for one plan item. Every number is the server's (explanation.*); nothing is calculated here. */
export interface MissionContext {
  nameOf: (skillKey: string) => string
  componentOf: (skillKey: string) => string | null
  battery: readonly BatteryItem[]
}

export interface MissionText {
  title: string
  /** e.g. "DSA · Two pointers" (component · skill) */
  skillLabel: string | null
  /** "What you'll do" for baseline items (the battery item's own description). */
  task: string | null
  why: string[]
  outcome: string | null
}

const ROUND_LABEL: Record<string, string> = {
  DSA: 'DSA', CS: 'CS', LLD: 'LLD / OOD', SYSTEM_DESIGN: 'System design', BEHAVIORAL: 'Behavioral',
  PROJECT_DEEP_DIVE: 'Project deep dive',
}

/** "DSA diagnostic A: 2 unseen MEDIUM problems…" -> title "DSA diagnostic A" and the rest as the task. */
export function batteryTitle(item: BatteryItem): { title: string; task: string | null } {
  const [head, ...rest] = item.name.split(':')
  const task = rest.join(':').trim()
  if (item.observation_kind === 'RECALL_QUIZ' && task.includes(',')) {
    const [topic, ...more] = task.split(',')
    return { title: `${head!.trim()}: ${topic!.trim()}`, task: capitalise(more.join(',').trim()) }
  }
  return { title: head!.trim(), task: task ? capitalise(tidyTask(task)) : null }
}

function batteryParts(item: PlanItem, battery: readonly BatteryItem[]): { title: string; task: string | null } {
  const found = battery.find((b) => b.key === item.battery_item_key)
  if (!found) return { title: `Baseline assessment ${item.battery_item_key ?? ''}`.trim(), task: null }
  return batteryTitle(found)
}

/** SELF_ASSESSMENT -> "self-assessment" (kind names that leaked into a description). */
function tidyTask(text: string): string {
  return text.replace(/\b[A-Z]{2,}(?:_[A-Z]+)+\b/g, (m) => m.toLowerCase().replace(/_/g, '-'))
}

function capitalise(text: string): string {
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : text
}

export function missionText(item: PlanItem, ctx: MissionContext): MissionText {
  const skill = item.skill
  const skillName = skill ? ctx.nameOf(skill) : null
  const component = skill ? ctx.componentOf(skill) : null
  const skillLabel = skillName
    ? `${component && skill ? `${areaLabel(skill, component, COMPONENT_LABEL)} · ` : ''}${skillName}`
    : null
  const stage = item.stage ? (STAGE_LABEL[item.stage] ?? prettyKey(item.stage)) : null
  const outcome = item.explanation.expected_outcome ? tidyCriteria(item.explanation.expected_outcome) : null

  switch (item.candidate_type) {
    case 'BASELINE': {
      const { title, task } = batteryParts(item, ctx.battery)
      return {
        title,
        skillLabel: null,
        task,
        why: ["This measures where you're starting from, so every plan after it is personal to you."],
        outcome,
      }
    }
    case 'REVISION':
      return {
        title: `Revise: ${skillName ?? 'a skill from earlier'}`,
        skillLabel,
        task: null,
        why: ['Reviewing at the right moment is what makes it stick.', ...reasonPhrases(item.reason_codes, ctx.nameOf, 1)],
        outcome,
      }
    case 'MOCK':
      return {
        title: `Mock interview: ${ROUND_LABEL[item.round_type ?? ''] ?? 'practice round'}`,
        skillLabel: null,
        task: null,
        why: ['A timed mock shows how your skills hold up under interview pressure.'],
        outcome,
      }
    case 'FINAL_SIMULATION':
      return {
        title: 'Full interview simulation',
        skillLabel: null,
        task: null,
        why: ['Your skills are ready for a full run-through of a real interview loop.'],
        outcome,
      }
    default: {
      const verb = item.candidate_type === 'MAINTENANCE' ? 'Keep sharp' : (stage ?? 'Practice')
      return {
        title: `${verb}: ${skillName ?? 'your focus skill'}`,
        skillLabel,
        task: null,
        why: whyFromExplanation(item, ctx),
        outcome,
      }
    }
  }
}

function whyFromExplanation(item: PlanItem, ctx: MissionContext): string[] {
  const out: string[] = []
  const { effective, current, target } = item.explanation
  const name = item.skill ? ctx.nameOf(item.skill) : 'This skill'
  const score = effective ?? current
  if (score != null && target != null) out.push(`Your ${name} score is ${score}, against a target of ${target}.`)
  out.push(...reasonPhrases(item.reason_codes, ctx.nameOf, score != null && target != null ? 1 : 2))
  return out
}

/** "a recall quiz" for the thing to record when the mission is done. */
export function recordLabel(kind: string): string {
  return OBSERVATION_LABEL[kind] ?? kind.toLowerCase().replace(/_/g, ' ')
}
