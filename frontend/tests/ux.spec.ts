import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ApiClient } from '../src/api/client'
import type { ProblemAttempt } from '../src/api/types'
import StatusPill from '../src/components/common/StatusPill.vue'
import EffectsPanel from '../src/components/missions/EffectsPanel.vue'
import AttemptForm from '../src/components/practice/AttemptForm.vue'
import { STATE_LABEL, type SemanticState } from '../src/presentation/language'
import { useSkillsStore } from '../src/stores/data'
import { SKILLS } from './fixtures'

beforeEach(() => setActivePinia(createPinia()))
const stubs = { RouterLink: RouterLinkStub }

describe('StatusPill', () => {
  it('always shows an icon AND a text label for every semantic state (never colour alone)', () => {
    for (const state of Object.keys(STATE_LABEL) as SemanticState[]) {
      const wrapper = mount(StatusPill, { props: { state } })
      expect(wrapper.text()).toBe(STATE_LABEL[state])
      expect(wrapper.find('svg').exists(), state).toBe(true)
      expect(wrapper.find('svg').attributes('aria-hidden')).toBe('true')
      expect(wrapper.attributes('data-state')).toBe(state)
    }
  })

  it('defines the ten required semantic states in plain words', () => {
    expect(STATE_LABEL).toMatchObject({
      critical: 'Critical', high: 'High', medium: 'Medium', healthy: 'Healthy', ready: 'Ready', due: 'Revision due',
      overdue: 'Overdue', blocked: 'Blocked', calibration: 'Calibrating', completed: 'Completed',
    })
  })

  it('accepts a custom label', () => {
    expect(mount(StatusPill, { props: { state: 'overdue', label: '3 overdue' } }).text()).toBe('3 overdue')
  })
})

describe('EffectsPanel', () => {
  it('lists skill, gap, review and readiness changes in human wording', () => {
    useSkillsStore().$patch({})
    const wrapper = mount(EffectsPanel, {
      global: { stubs },
      props: {
        effects: {
          run_id: 4,
          skill_deltas: [{ skill_key: 'graph.traversal', before: null, after: { score: 30, effective: 15, level: 1, confidence: 'LOW' } }],
          gap_deltas: [{ skill_key: 'graph.traversal', before: { priority: 100, status: 'UNASSESSED' }, after: { priority: 98, status: 'CRITICAL' } }],
          revision_changes: [{ item_key: 'PROBLEM:17', change: 'CREATED', due_date: '2026-10-07' }],
          readiness_change: { before: 'NOT_MEASURED', after: 'FOUNDATION', blockers_added: [], blockers_removed: [] },
        },
      },
    })
    const text = wrapper.text()
    expect(text).toContain('What changed')
    expect(text).toContain('gap: Not measured yet → Critical')
    expect(text).toMatch(/Review of a problem you worked on\s*scheduled for 7 Oct/)
    expect(text).toContain('Readiness: Not measured yet → Foundation')
    expect(text).not.toMatch(/PROBLEM:17|CRITICAL|NOT_MEASURED/)
  })

  it('does not report an unchanged readiness state as a change', () => {
    const wrapper = mount(EffectsPanel, {
      global: { stubs },
      props: { effects: { run_id: 4, skill_deltas: [], readiness_change: { before: 'DEVELOPING', after: 'DEVELOPING', blockers_added: [], blockers_removed: [] } } },
    })
    expect(wrapper.text()).not.toContain('Readiness:')
  })

  it('uses catalog names when the skills are loaded', async () => {
    const skills = useSkillsStore()
    skills.data = SKILLS
    const wrapper = mount(EffectsPanel, {
      global: { stubs },
      props: { effects: { run_id: 1, skill_deltas: [{ skill_key: 'graph.traversal', before: null, after: { score: 30, effective: 15, level: 1, confidence: 'LOW' } }] } },
    })
    expect(wrapper.text()).toContain('Graphs: BFS and DFS')
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

  it('keeps solving focused: only the clock, the notes box and one action while the timer runs', async () => {
    const client: ApiClient = { get: vi.fn() as ApiClient['get'], post: vi.fn() }
    const wrapper = mount(AttemptForm, { global: { stubs }, props: { problemId: 1, client } })
    await wrapper.find('[data-testid="start"]').trigger('click')
    expect(wrapper.find('[data-testid="timer"]').exists()).toBe(true)
    expect(wrapper.find('textarea').exists()).toBe(true)
    expect(wrapper.findAll('button')).toHaveLength(1)
    expect(wrapper.find('[data-testid="outcome-PASS"]').exists()).toBe(false)
  })
})
