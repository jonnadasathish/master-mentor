import type { AssessmentInput, Familiarity } from '../api/types'

/** Form state of the generic assessment form (UI units: minutes; points 0-100 per observed skill). */
export interface AssessmentForm {
  sourceKey: string
  points: Record<string, number | null> // skill key -> points; null = not observed this time
  notesUsed: boolean
  referenceUsed: boolean
  hints: number
  timed: boolean
  limitMinutes: number | null
  minutes: number | null
  followupPoints: number | null
  notes: string
}

export function emptyAssessmentForm(sourceKey: string, skills: string[]): AssessmentForm {
  return {
    sourceKey,
    points: Object.fromEntries(skills.map((s) => [s, null])),
    notesUsed: false,
    referenceUsed: false,
    hints: 0,
    timed: false,
    limitMinutes: null,
    minutes: null,
    followupPoints: null,
    notes: '',
  }
}

/** An emptied number input yields '' (v-model.number); treat it as "not given". */
export function given(value: unknown): number | null {
  return typeof value === 'number' && !Number.isNaN(value) ? value : null
}

const inRange = (v: unknown, lo: number, hi: number) => {
  const n = given(v)
  return n === null || (Number.isInteger(n) && n >= lo && n <= hi)
}

/** Client-side checks for fast feedback only; the server validates everything again. */
export function assessmentErrors(form: AssessmentForm): string[] {
  const errors: string[] = []
  const observed = Object.values(form.points).filter((p) => given(p) !== null)
  if (!form.sourceKey.trim()) errors.push('Give the prompt / exercise a key.')
  if (!observed.length) errors.push('Score at least one skill (0–100).')
  if (!Object.values(form.points).every((p) => inRange(p, 0, 100))) errors.push('Points must be 0–100.')
  if (!inRange(form.followupPoints, 0, 100)) errors.push('Follow-up points must be 0–100.')
  if (form.timed && (given(form.limitMinutes) === null || given(form.minutes) === null)) {
    errors.push('Timed needs a limit and a time.')
  }
  return errors
}

export function buildAssessmentPayload(
  kind: string,
  form: AssessmentForm,
  requestId: string,
  batteryItemKey?: string,
  revisionItemKey?: string,
): AssessmentInput {
  const payload: AssessmentInput = {
    kind,
    source_key: form.sourceKey.trim(),
    notes_used: form.notesUsed,
    reference_used: form.referenceUsed,
    hints_used: form.hints,
    timed: form.timed,
    skills: Object.entries(form.points)
      .map(([skill, points]) => ({ skill, outcome_points: given(points) }))
      .filter((s): s is { skill: string; outcome_points: number } => s.outcome_points !== null),
    client_request_id: requestId,
  }
  const limit = given(form.limitMinutes)
  const minutes = given(form.minutes)
  if (form.timed && limit !== null && minutes !== null) {
    payload.time_limit_seconds = limit * 60
    payload.time_seconds = minutes * 60
  }
  const followup = given(form.followupPoints)
  if (followup !== null) payload.followup_points = followup
  if (form.notes.trim()) payload.notes = form.notes.trim()
  if (batteryItemKey) {
    payload.battery_item_key = batteryItemKey
    payload.mode = 'BASELINE'
  }
  if (revisionItemKey) {
    payload.revision_item_key = revisionItemKey
    payload.mode = 'REVISION'
  }
  return payload
}

export function buildSweepPayload(
  answers: Record<string, Familiarity | null>,
  requestId: string,
): { entries: { skill: string; familiarity: Familiarity }[]; client_request_id: string } {
  return {
    entries: Object.entries(answers)
      .filter((entry): entry is [string, Familiarity] => entry[1] !== null)
      .map(([skill, familiarity]) => ({ skill, familiarity })),
    client_request_id: requestId,
  }
}
