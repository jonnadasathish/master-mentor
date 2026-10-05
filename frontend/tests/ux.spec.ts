import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ApiClient } from '../src/api/client'
import type { ProblemAttempt } from '../src/api/types'
import AttemptForm from '../src/components/AttemptForm.vue'
import EffectsPanel from '../src/components/EffectsPanel.vue'
import StatusBadge from '../src/components/StatusBadge.vue'

beforeEach(() => setActivePinia(createPinia()))
const stubs = { RouterLink: RouterLinkStub }

describe('StatusBadge', () => {
  it('always shows a text label next to the icon (never color alone)', () => {
    for (const status of ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'BLOCKED', 'PARKED', 'UNASSESSED', 'NONE']) {
      const text = mount(StatusBadge, { props: { status, priority: 42 } }).text()
      expect(text).toContain(status.toLowerCase())
    }
    expect(mount(StatusBadge, { props: { status: 'CRITICAL', priority: 89 } }).text()).toBe('⛔ critical 89')
  })
})

describe('EffectsPanel', () => {
  it('lists skill, gap, revision and readiness changes from the server', () => {
    const wrapper = mount(EffectsPanel, {
      global: { stubs },
      props: {
        effects: {
          run_id: 4,
          skill_deltas: [{ skill_key: 'heap.top_k', before: null, after: { score: 30, effective: 15, level: 1, confidence: 'LOW' } }],
          gap_deltas: [{ skill_key: 'heap.top_k', before: { priority: 100, status: 'UNASSESSED' }, after: { priority: 98, status: 'CRITICAL' } }],
          revision_changes: [{ item_key: 'PROBLEM:17', change: 'CREATED', due_date: '2026-10-07' }],
          readiness_change: { before: 'NOT_MEASURED', after: 'NOT_MEASURED', blockers_added: [], blockers_removed: [] },
        },
      },
    })
    const text = wrapper.text()
    expect(text).toContain('Gap heap.top_k: unassessed 100 → critical 98')
    expect(text).toContain('Revision PROBLEM:17: created, due 2026-10-07')
    expect(text).not.toContain('Readiness:')  // unchanged state is not shown as a change
  })
})

describe('AttemptForm correction', () => {
  it('prefills from the original and posts a correction (never an edit)', async () => {
    const original = {
      id: 5, problem: { id: 27, key: 'LEETCODE:number-of-islands', title: 'Islands', difficulty: 'MEDIUM', source: 'CATALOG' },
      attempted_at: '2026-10-03T06:00:00Z', attempted_on: '2026-10-03', mode: 'PRACTICE', outcome: 'FAIL', seen_elsewhere: false,
      hints_used: 1, solution_viewed: false, pattern_identified: false, timed: false, time_limit_seconds: null, time_seconds: 1800,
      explanation_score: null, complexity_correct: null, followup_solved: null, execution_rubric: null, mistakes: ['WRONG_PATTERN'],
      self_rating_before: 3, self_rating_after: null, notes: null, supersedes_id: null, superseded_by_id: null, is_current: true,
      created_at: '2026-10-03T06:01:00Z',
    } as ProblemAttempt
    const post = vi.fn().mockResolvedValue({ data: { id: 6 }, meta: {}, effects: { run_id: 2, skill_deltas: [] } })
    const client: ApiClient = { get: vi.fn() as ApiClient['get'], post }
    const wrapper = mount(AttemptForm, { global: { stubs }, props: { problemId: 27, client, correctionOf: original } })
    expect((wrapper.find('[data-testid="minutes"]').element as HTMLInputElement).value).toBe('30')
    await wrapper.find('[data-testid="outcome-PARTIAL"]').setValue(true)
    await wrapper.find('[data-testid="log-form"]').trigger('submit')
    await flushPromises()
    const [path, body] = post.mock.calls[0]!
    expect(path).toBe('/problem-attempts/5/corrections')
    expect(body).toMatchObject({ problem_id: 27, outcome: 'PARTIAL', time_seconds: 1800, attempted_at: '2026-10-03T06:00:00Z', mistakes: ['WRONG_PATTERN'] })
    expect(wrapper.find('[data-testid="recorded"]').text()).toBe('Correction recorded (the original is kept).')
  })
})
