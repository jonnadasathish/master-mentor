import type { Outcome, ProblemAttempt, ProblemAttemptInput } from '../api/types'

/** Form state of the attempt form (UI units: minutes). */
export interface AttemptForm {
  outcome: Outcome | null
  minutes: number | null
  hints: number
  mistakes: string[]
  confidenceBefore: number | null
  confidenceAfter: number | null
  explanation: number | null
  complexityCorrect: boolean | null
  notes: string
  solutionViewed: boolean
  patternIdentified: boolean | null
  seenElsewhere: boolean
  timed: boolean
  limitMinutes: number | null
  followupSolved: boolean | null
  attemptedAt: string | null // ISO-8601 with offset; null = now (server clock)
}

export function emptyForm(): AttemptForm {
  return {
    outcome: null,
    minutes: null,
    hints: 0,
    mistakes: [],
    confidenceBefore: null,
    confidenceAfter: null,
    explanation: null,
    complexityCorrect: null,
    notes: '',
    solutionViewed: false,
    patternIdentified: null,
    seenElsewhere: false,
    timed: false,
    limitMinutes: null,
    followupSolved: null,
    attemptedAt: null,
  }
}

/** Prefill for a correction: the corrected version keeps the original instant unless changed. */
export function formFromAttempt(a: ProblemAttempt): AttemptForm {
  return {
    outcome: a.outcome,
    minutes: a.time_seconds === null ? null : Math.round(a.time_seconds / 60),
    hints: a.hints_used,
    mistakes: [...a.mistakes],
    confidenceBefore: a.self_rating_before,
    confidenceAfter: a.self_rating_after,
    explanation: a.explanation_score,
    complexityCorrect: a.complexity_correct,
    notes: a.notes ?? '',
    solutionViewed: a.solution_viewed,
    patternIdentified: a.pattern_identified,
    seenElsewhere: a.seen_elsewhere,
    timed: a.timed,
    limitMinutes: a.time_limit_seconds === null ? null : Math.round(a.time_limit_seconds / 60),
    followupSolved: a.followup_solved,
    attemptedAt: a.attempted_at,
  }
}

/** Client-side checks only for fast feedback; the server re-validates everything. */
export function formErrors(form: AttemptForm): string[] {
  const errors: string[] = []
  if (form.outcome === null) errors.push('Choose a result.')
  if (form.minutes === null || form.minutes < 0) errors.push('Enter the time spent (minutes).')
  if (form.hints < 0) errors.push('Hints cannot be negative.')
  if (form.timed && (form.limitMinutes === null || form.limitMinutes < 1)) errors.push('Enter the time limit.')
  return errors
}

/** Unit conversion and omission of unset optional fields. No interpretation of the values. */
export function buildAttemptPayload(problemId: number, form: AttemptForm, requestId: string): ProblemAttemptInput {
  if (form.outcome === null || form.minutes === null) throw new Error('form is incomplete')
  const payload: ProblemAttemptInput = {
    problem_id: problemId,
    outcome: form.outcome,
    time_seconds: Math.round(form.minutes * 60),
    hints_used: form.hints,
    mistakes: [...form.mistakes],
    solution_viewed: form.solutionViewed,
    seen_elsewhere: form.seenElsewhere,
    timed: form.timed,
    client_request_id: requestId,
  }
  if (form.timed && form.limitMinutes !== null) payload.time_limit_seconds = Math.round(form.limitMinutes * 60)
  if (form.confidenceBefore !== null) payload.self_rating_before = form.confidenceBefore
  if (form.confidenceAfter !== null) payload.self_rating_after = form.confidenceAfter
  if (form.explanation !== null) payload.explanation_score = form.explanation
  if (form.complexityCorrect !== null) payload.complexity_correct = form.complexityCorrect
  if (form.patternIdentified !== null) payload.pattern_identified = form.patternIdentified
  if (form.followupSolved !== null) payload.followup_solved = form.followupSolved
  if (form.notes.trim()) payload.notes = form.notes.trim()
  if (form.attemptedAt) payload.attempted_at = form.attemptedAt
  return payload
}

export function newRequestId(): string {
  return globalThis.crypto?.randomUUID?.() ?? `req-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}
