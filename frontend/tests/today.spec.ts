import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { HttpClient } from '../src/api/client'
import type { PlanItem } from '../src/api/types'
import PlanItemCard from '../src/components/PlanItemCard.vue'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn() }))
vi.mock('../src/api', () => ({ api }))

import TodayView from '../src/views/today/TodayView.vue'

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

const stubs = { RouterLink: RouterLinkStub }

function item(extra: Partial<PlanItem> = {}): PlanItem {
  return {
    id: 7, position: 1, candidate_type: 'GAP', candidate_key: 'GAP:heap.top_k', skill: 'heap.top_k', stage: 'TIMED',
    minutes: 40, candidate_score: 57,
    template: { key: 'dsa.timed', observation: { kind: 'ATTEMPT' }, pass_rule: 'outcome == PASS', output_level: 4, next_on_pass: 'EXPLAIN' },
    problems: [{ id: 17, key: 'LEETCODE:kth-largest', title: 'Kth Largest', difficulty: 'MEDIUM', url: null }],
    revision_item_key: null, battery_item_key: null, round_type: null, reason_codes: ['BELOW_FLOOR'],
    explanation: { evidence: 'BELOW_FLOOR', effective: 44, target: 80 }, status: 'PENDING', skip_reason: null,
    observation_type: null, observation_id: null, no_evidence: false, carried_over_from_id: null, started_at: null,
    completed_at: null, ...extra,
  }
}

function client(): HttpClient {
  return { get: vi.fn(), post: vi.fn().mockResolvedValue({ data: {}, meta: {} }), patch: vi.fn() } as unknown as HttpClient
}

describe('TodayView', () => {
  it('shows the frozen plan, the mentor message and calibration banner as returned', async () => {
    api.get.mockResolvedValue({
      data: {
        plan_date: '2026-11-02', phase: 'BUILD', weeks_left: '34.0', goal_exists: true,
        calibration: { active: true, assessed: 0, required: 123, assessed_pct: 0, battery_done: 0, battery_total: 12, next_item: 'M0-B01' },
        readiness: { state: 'NOT_MEASURED', weighted_score: 0, limiting_component: null, blockers: [] },
        top_gaps: [], revisions: { due: 0, overdue: 0, backlog_minutes: 0, cap_minutes: 36 },
        plan: {
          id: 1, plan_date: '2026-11-02', run_id: 3, ruleset_version: 'v1', budget_minutes: 90, allocated_minutes: 75,
          unallocated_minutes: 15, done_minutes: 0, phase: 'BUILD', calibration_mode: true, regenerated_count: 0,
          items: [item({ candidate_type: 'BASELINE', candidate_key: 'BASE:M0-B01', battery_item_key: 'M0-B01', template: null, problems: [], skill: null })],
          stop_list: [], dropped: [], message: { rule: 'CALIBRATION', text: 'Calibration: 0/123 required skills measured.', payload: {} },
        },
      },
      meta: { run_id: 3 },
    })
    const wrapper = mount(TodayView, { global: { stubs } })
    await flushPromises()
    expect(wrapper.find('[data-testid="mentor-message"]').text()).toBe('Calibration: 0/123 required skills measured.')
    expect(wrapper.find('[data-testid="today-header"]').text()).toContain('Calibration · 0/123 skills measured · battery 0/12 · 34.0 weeks left · BUILD')
    await wrapper.find('[data-testid="message-why"]').trigger('click')
    expect(wrapper.find('[data-testid="message-payload"]').text()).toContain('CALIBRATION')
    expect(wrapper.find('[data-testid="today-footer"]').text()).toContain('backlog 0 min (cap 36)')
    expect(wrapper.find('[data-testid="plan-item-1"]').text()).toContain('Baseline M0-B01')
    api.post.mockResolvedValue(await api.get.mock.results[0]!.value)  // regenerate returns the same Today shape
    await wrapper.find('[data-testid="regenerate"]').trigger('click')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/plan/today/regenerate', {})
    expect(wrapper.find('[data-testid="mentor-message"]').exists()).toBe(true)
  })
})

describe('PlanItemCard', () => {
  it('posts no-evidence, defer and skip with a reason', async () => {
    const c = client()
    const wrapper = mount(PlanItemCard, { global: { stubs }, props: { item: item(), client: c } })
    expect(wrapper.text()).toContain('1. heap.top_k')
    expect(wrapper.text()).toContain('Done when: outcome == PASS')
    await wrapper.find('[data-testid="no-evidence-1"]').trigger('click')
    await wrapper.find('[data-testid="defer-1"]').trigger('click')
    await wrapper.find('[data-testid="skip-1"]').trigger('click')
    await wrapper.find('[data-testid="skip-1-TOO_HARD"]').trigger('click')
    await flushPromises()
    expect((c.post as ReturnType<typeof vi.fn>).mock.calls).toEqual([
      ['/plan/items/7/complete', { no_evidence: true }],
      ['/plan/items/7/defer', {}],
      ['/plan/items/7/skip', { skip_reason: 'TOO_HARD' }],
    ])
    expect(wrapper.emitted('changed')).toHaveLength(3)
  })

  it('logs an attempt through the plan item so the server links it', async () => {
    const c = client()
    ;(c.post as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { item: {}, observation: { id: 3 } }, meta: {}, effects: { run_id: 1, skill_deltas: [] } })
    const wrapper = mount(PlanItemCard, { global: { stubs }, props: { item: item(), client: c } })
    await wrapper.find('[data-testid="log-1"]').trigger('click')
    await wrapper.find('[data-testid="log-direct"]').trigger('click')
    expect(wrapper.emitted('completed')).toBeUndefined()
    await wrapper.find('[data-testid="outcome-PASS"]').setValue(true)
    await wrapper.find('[data-testid="minutes"]').setValue('30')
    await wrapper.find('[data-testid="log-form"]').trigger('submit')
    await flushPromises()
    const [path, body] = (c.post as ReturnType<typeof vi.fn>).mock.calls[0]!
    expect(path).toBe('/plan/items/7/complete')
    expect(body).toMatchObject({ observation: { type: 'ATTEMPT', body: { problem_id: 17, outcome: 'PASS', time_seconds: 1800 } } })
    expect(wrapper.emitted('completed')?.[0]).toEqual([{ run_id: 1, skill_deltas: [] }])
  })

  it('Start shows the mission timer against the template limit', async () => {
    vi.useFakeTimers()
    let now = 1_000_000
    const c = client()
    const withWhy = item({ explanation: { evidence: 'BELOW_FLOOR', expected_outcome: 'pass (L4 evidence)', priority: 57 } })
    const wrapper = mount(PlanItemCard, { global: { stubs }, props: { item: withWhy, client: c, now: () => now } })
    await wrapper.find('[data-testid="start-1"]').trigger('click')
    await flushPromises()
    now += 65_000
    vi.advanceTimersByTime(1000)
    await wrapper.vm.$nextTick()
    expect((c.post as ReturnType<typeof vi.fn>).mock.calls[0]).toEqual(['/plan/items/7/start', {}])
    expect(wrapper.find('[data-testid="timer-1"]').text()).toBe('⏱ 01:05 / 40:00')
    await wrapper.find('[data-testid="why-1"]').trigger('click')
    expect(wrapper.find('[data-testid="why-panel-1"]').text()).toContain('BELOW_FLOOR')
    vi.useRealTimers()
  })

  it('hides actions for finished items', () => {
    const wrapper = mount(PlanItemCard, { global: { stubs }, props: { item: item({ status: 'DONE' }), client: client() } })
    expect(wrapper.find('[data-testid="log-1"]').exists()).toBe(false)
  })
})
