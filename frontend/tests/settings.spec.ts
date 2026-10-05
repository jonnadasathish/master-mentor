import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../src/api/client'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn() }))
vi.mock('../src/api', () => ({ api }))

import SettingsView from '../src/views/settings/SettingsView.vue'
import SkillsView from '../src/views/skills/SkillsView.vue'

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

const ACTIVE = {
  id: 2, profile_key: 'backend_fullstack_sde2', target_date: '2027-06-28', weekday_budgets: [90, 90, 90, 90, 90, 75, 75],
  weekly_minutes: 600, valid_from: '2026-10-04', valid_to: null, is_active: true, created_at: '2026-10-04T12:00:00Z',
  phase: 'BUILD', weeks_left: '38.1',
}

describe('SettingsView', () => {
  it('creates the first goal with POST when none exists', async () => {
    api.get.mockImplementation((path: string) => {
      if (['/stories', '/projects', '/prompts', '/catalog/skills'].includes(path)) return Promise.resolve({ data: [], meta: {} })
      if (path === '/settings') return Promise.resolve({ data: { timezone: 'Asia/Kolkata', display_name: 'Owner' }, meta: {} })
      if (path === '/goals/history') return Promise.resolve({ data: [], meta: { count: 0 } })
      return Promise.reject(new ApiError('NOT_FOUND', 'No active goal', 404))
    })
    api.post.mockResolvedValue({ data: ACTIVE, meta: {} })
    const wrapper = mount(SettingsView)
    await flushPromises()
    await wrapper.find('[data-testid="target-date"]').setValue('2027-06-28')
    await wrapper.find('[data-testid="budget-6"]').setValue('60')
    await wrapper.find('[data-testid="goal-form"]').trigger('submit')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/goals', { target_date: '2027-06-28', weekday_budgets: [90, 90, 90, 90, 90, 75, 60] })
    expect(api.patch).not.toHaveBeenCalled()
  })

  it('patches the active goal and sends only a changed target date', async () => {
    api.get.mockImplementation((path: string) => {
      if (['/stories', '/projects', '/prompts', '/catalog/skills'].includes(path)) return Promise.resolve({ data: [], meta: {} })
      if (path === '/settings') return Promise.resolve({ data: { timezone: 'Asia/Kolkata', display_name: 'Owner' }, meta: {} })
      if (path === '/goals/history') return Promise.resolve({ data: [ACTIVE], meta: { count: 1 } })
      return Promise.resolve({ data: ACTIVE, meta: {} })
    })
    api.patch.mockResolvedValue({ data: ACTIVE, meta: {} })
    const wrapper = mount(SettingsView)
    await flushPromises()
    expect(wrapper.find('[data-testid="goal-summary"]').text()).toContain('BUILD')
    await wrapper.find('[data-testid="budget-0"]').setValue('120')
    await wrapper.find('[data-testid="goal-form"]').trigger('submit')
    await flushPromises()
    expect(api.patch).toHaveBeenCalledWith('/goals/active', { weekday_budgets: [120, 90, 90, 90, 90, 75, 75] })
  })
})

describe('SkillsView', () => {
  it('shows the first 3 actionable gaps in engine rank order without recomputing', async () => {
    const skill = (key: string, status: string, priority: number, rank: number) => ({
      key, name: key, group: 'g', component: 'dsa', tier: 'T1', importance: 100, target_score: 80, floor_score: 65, required: true,
      state: { score: 40, effective_score: 33, level: 2, confidence: 'MEDIUM', label: 'WEAK', peak_score: 40, evidence_count: 3,
        distinct_sources: 2, last_practiced_on: '2026-10-01', last_observed_on: '2026-10-01', reality_capped: false, declared_unknown: false, assessed: true },
      gap: { status, priority, rank, primary_gap_type: 'PRACTICE', focus_stage: 'INDEPENDENT', focus_skill: key, reason_codes: [], blocked_by: [], parked_reason: null },
    })
    api.get.mockResolvedValue({
      data: [skill('b', 'HIGH', 50, 3), skill('a', 'CRITICAL', 63, 1), skill('c', 'BLOCKED', 90, 2), skill('d', 'LOW', 12, 5), skill('e', 'MEDIUM', 30, 4)],
      meta: { as_of_date: '2026-11-02', run_id: 3, ruleset_version: 'v1' },
    })
    const wrapper = mount(SkillsView, { global: { stubs: { RouterLink: RouterLinkStub } } })
    await flushPromises()
    const top = wrapper.find('[data-testid="top-gaps"]').findAll('li').map((li) => li.text().split(' —')[0])
    expect(top).toEqual(['a', 'b', 'e'])
  })
})
