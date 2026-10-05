import { describe, expect, it } from 'vitest'
import { buildAttemptPayload, emptyForm, formErrors } from '../src/practice/payload'

describe('attempt payload', () => {
  it('converts minutes to seconds and omits unset optional fields', () => {
    const form = { ...emptyForm(), outcome: 'PASS' as const, minutes: 18, confidenceBefore: 4, explanation: 8, complexityCorrect: true }
    expect(buildAttemptPayload(1, form, 'req-abcdefgh')).toEqual({
      problem_id: 1,
      outcome: 'PASS',
      time_seconds: 1080,
      hints_used: 0,
      mistakes: [],
      solution_viewed: false,
      seen_elsewhere: false,
      timed: false,
      client_request_id: 'req-abcdefgh',
      self_rating_before: 4,
      explanation_score: 8,
      complexity_correct: true,
    })
  })

  it('keeps false booleans, mistakes and the time limit for timed attempts', () => {
    const form = {
      ...emptyForm(), outcome: 'FAIL' as const, minutes: 31, hints: 2, mistakes: ['WRONG_PATTERN'],
      patternIdentified: false, timed: true, limitMinutes: 30, notes: '  stuck on BFS  ',
    }
    const payload = buildAttemptPayload(27, form, 'req-abcdefgh')
    expect(payload).toMatchObject({
      outcome: 'FAIL', time_seconds: 1860, hints_used: 2, mistakes: ['WRONG_PATTERN'],
      pattern_identified: false, timed: true, time_limit_seconds: 1800, notes: 'stuck on BFS',
    })
  })

  it('reports missing result and time before contacting the server', () => {
    expect(formErrors(emptyForm())).toEqual(['Choose a result.', 'Enter the time spent (minutes).'])
    expect(formErrors({ ...emptyForm(), outcome: 'PASS', minutes: 10, timed: true })).toEqual(['Enter the time limit.'])
  })
})
