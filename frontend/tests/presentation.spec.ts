import { describe, expect, it } from 'vitest'
import { ApiError } from '../src/api/client'
import { barPercent, formatMinutes, greetingFor, longDate, plural, prettyKey, shortDate } from '../src/presentation/format'
import { categoryForComponent, stateFromGapStatus } from '../src/presentation/language'
import { missionText } from '../src/presentation/mission'
import { friendlyError, friendlyFromCode } from '../src/presentation/errors'
import { reasonPhrases } from '../src/presentation/reasons'
import { evidenceDetail, evidenceTitle, whyWeak } from '../src/presentation/skill'
import { humaniseKeys, tidyCriteria } from '../src/presentation/text'
import { isActive, NAV_ITEMS } from '../src/router/nav'
import { baseline, baselineItem, GAP_DETAIL, planItem, SKILL_DETAIL } from './fixtures'

describe('format', () => {
  it('formats minutes, widths and greetings without inventing anything', () => {
    expect([0, 35, 60, 95, 510].map(formatMinutes)).toEqual(['0 min', '35 min', '1h', '1h 35m', '8h 30m'])
    expect(barPercent(43, 80)).toBeCloseTo(53.75)
    expect([barPercent(null, 80), barPercent(5, 0), barPercent(200, 80), barPercent(-3, 80)]).toEqual([0, 0, 100, 0])
    expect([greetingFor(2), greetingFor(8), greetingFor(14), greetingFor(20)]).toEqual(['Good evening', 'Good morning', 'Good afternoon', 'Good evening'])
    expect(plural(1, 'day')).toBe('1 day')
    expect(plural(3, 'review')).toBe('3 reviews')
    expect(shortDate('2026-10-05')).toBe('5 Oct')
    expect(shortDate(null)).toBe('—')
    expect(longDate('2026-10-05')).toBe('Monday, 5 October')
    expect(prettyKey('two_pointers.core')).toBe('Core')
  })
})

describe('language', () => {
  it('maps gap statuses to the semantic states', () => {
    expect(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'NONE', 'UNASSESSED', 'BLOCKED', 'PARKED'].map(stateFromGapStatus)).toEqual([
      'critical', 'high', 'medium', 'low', 'healthy', 'calibration', 'blocked', 'parked',
    ])
  })
  it('groups components into the five Prepare areas', () => {
    expect(categoryForComponent('coding')?.slug).toBe('dsa')
    expect(categoryForComponent('project')?.slug).toBe('behavioral')
    expect(categoryForComponent('system_design')?.slug).toBe('system-design')
  })
})

describe('reasons', () => {
  const name = (k: string) => (k === 'os.synchronization' ? 'Synchronization' : k)
  it('words only the codes the server sent, most actionable first, capped', () => {
    expect(reasonPhrases(['LARGE_GAP', 'REPEATED_FAILURE', 'HIGH_IMPORTANCE'], name, 2)).toEqual([
      'Recent attempts keep failing.', 'It is a long way from your target.',
    ])
    expect(reasonPhrases(['UNLOCKS:os.synchronization'], name)).toEqual(['Unlocks Synchronization.'])
    expect(reasonPhrases(['SOMETHING_NEW', 'TRACK_FLOOR'], name)).toEqual([])
  })
})

describe('text', () => {
  it('turns technical criteria into plain phrases', () => {
    expect(tidyCriteria('outcome_points >= 70 (L3 evidence)')).toBe('A score of 70 or more')
    expect(tidyCriteria('outcome_points >= 70 per skill (L3 evidence)')).toBe('A score of 70 or more on each skill')
    expect(tidyCriteria('followup_points >= 70')).toBe('A follow-up score of 70 or more')
  })
  it('swaps identifiers for names, longest key first', () => {
    const names: [string, string][] = [['graph', 'G'], ['graph.traversal', 'Graphs'], ['M0-B01', 'Familiarity sweep']]
    expect(humaniseKeys('Do graph.traversal after M0-B01.', names)).toBe('Do Graphs after Familiarity sweep.')
  })
})

describe('mission wording', () => {
  const ctx = { nameOf: (k: string) => (k === 'sd.caching' ? 'Caching' : k), componentOf: () => 'system_design', battery: baseline(0).items }
  it('titles by stage and skill and quotes only server numbers', () => {
    const t = missionText(planItem({ skill: 'sd.caching', stage: 'GUIDED', explanation: { effective: 20, target: 80, expected_outcome: 'outcome_points >= 70' } }), ctx)
    expect(t.title).toBe('Guided practice: Caching')
    expect(t.skillLabel).toBe('System Design · Caching')
    expect(t.why[0]).toBe('Your Caching score is 20, against a target of 80.')
    expect(t.outcome).toBe('A score of 70 or more')
  })
  it('does not invent a score when the server gave none', () => {
    const t = missionText(planItem({ skill: 'sd.caching', explanation: { expected_outcome: 'x' }, reason_codes: ['UNASSESSED'] }), ctx)
    expect(t.why.join(' ')).not.toMatch(/\d/)
    expect(t.why).toContain("We haven't measured this yet.")
  })
  it('words revisions, mocks and simulations', () => {
    expect(missionText(planItem({ candidate_type: 'REVISION', skill: 'sd.caching' }), ctx).title).toBe('Revise: Caching')
    expect(missionText(planItem({ candidate_type: 'MOCK', round_type: 'SYSTEM_DESIGN', skill: null }), ctx).title).toBe('Mock interview: System design')
    expect(missionText(planItem({ candidate_type: 'FINAL_SIMULATION', skill: null }), ctx).title).toBe('Full interview simulation')
    expect(missionText(baselineItem({ battery_item_key: 'M0-B01' }), ctx).task).toBe('Self-assessment (NONE/SOME/SOLID) for every required skill')
  })
})

describe('skill explanations', () => {
  it('builds "why you are weak" from the gap metrics and codes', () => {
    const lines = whyWeak(GAP_DETAIL, (k) => k)
    expect(lines.slice(0, 3)).toEqual([
      '3 of your last 5 attempts failed.', 'You missed the pattern in 3 of your last 4 attempts.', 'You last practised this 12 days ago.',
    ])
    expect(lines).toContain('DSA overall is at 58; it needs 72.')
    expect(whyWeak({ ...GAP_DETAIL, metrics: { ...GAP_DETAIL.metrics, speed_median_ratio_bp: 15000 } }, (k) => k)).toContain('You usually take 150% of the time limit.')
  })
  it('titles evidence rows in plain words', () => {
    const [attempt, quiz] = SKILL_DETAIL.evidence
    expect(evidenceTitle(attempt!)).toBe('Practice attempt')
    expect(evidenceTitle(quiz!)).toBe('Recall quiz')
    expect(evidenceDetail(attempt!)).toBe('Scored 40 · over the time limit')
    expect(evidenceDetail({ ...quiz!, kind: 'SELF_ASSESSMENT', familiarity: 'NONE' })).toBe('New to you')
    expect(evidenceDetail({ ...quiz!, is_scoring: false })).toBe('Not scored')
  })
})

describe('errors', () => {
  it('speaks plainly and keeps codes out of the headline', () => {
    expect(friendlyError(new ApiError('NETWORK_ERROR', 'x', null)).title).toBe("Master Mentor can't reach the preparation engine right now.")
    expect(friendlyError(new ApiError('BACKEND_UNAVAILABLE', 'x', 503)).title).toContain("can't reach the preparation engine")
    expect(friendlyError(new ApiError('NOT_FOUND', 'x', 404)).title).toBe("We couldn't find that.")
    expect(friendlyError(new ApiError('INVALID_STATE', 'Plan already started.', 409)).body).toBe('Plan already started.')
    expect(friendlyError(new Error('boom')).title).toBe('Something went wrong.')
    expect(friendlyFromCode('NETWORK_ERROR').title).toContain("can't reach")
  })
})

describe('navigation matching', () => {
  const item = (key: string) => NAV_ITEMS.find((i) => i.key === key)!
  it('marks Today only at the root and groups deep pages under their section', () => {
    expect(isActive(item('today'), '/')).toBe(true)
    expect(isActive(item('today'), '/prepare')).toBe(false)
    expect(isActive(item('prepare'), '/prepare/dsa/problems')).toBe(true)
    expect(isActive(item('prepare'), '/skills/graph.traversal')).toBe(true)
    expect(isActive(item('progress'), '/review')).toBe(true)
    expect(isActive(item('settings'), '/settings/developer')).toBe(true)
    expect(isActive(item('revise'), '/revise')).toBe(true)
  })
})
