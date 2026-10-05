import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn() }))
vi.mock('../src/api', () => ({ api }))

import ProgressView from '../src/views/progress/ProgressView.vue'

beforeEach(() => setActivePinia(createPinia()))

describe('ProgressView', () => {
  it('headlines the state, blocker count and limiting component (never a percentage)', async () => {
    api.get.mockImplementation((path: string) =>
      Promise.resolve(
        path === '/readiness'
          ? {
              data: {
                as_of_date: '2026-11-02', run_id: 9, ruleset_version: 'v1', state: 'FOUNDATION', simulation_eligible: false,
                lapsed: false, weighted_score: 76, limiting_component: 'system_design',
                components: [{ key: 'system_design', name: 'System Design', score: 42, gate: 72, stretch: 80, weight: 18,
                  assessed_pct: 100, medium_conf_pct: 100, passes_gate: false }],
                gates: [{ gate: 'G0', passed: true, failing: 0 }, { gate: 'G1', passed: false, failing: 1 }],
                blockers: [{ gate: 'G1', subject: 'system_design', kind: 'component', actual: 42, required: 45, deficit: 3,
                  message: 'System Design 42 < 45', skills: ['sd.caching'] }],
                all_failing: [],
              },
              meta: {},
            }
          : path === '/weekly-reviews/latest' ? Promise.reject(new Error('none')) as never : { data: [{ date: '2026-11-02', state: 'FOUNDATION', weighted_score: 76, limiting_component: 'system_design', components: {}, blockers: 1 }], meta: {} },
      ),
    )
    const wrapper = mount(ProgressView, { global: { stubs: { RouterLink: RouterLinkStub } } })
    await flushPromises()
    expect(wrapper.find('[data-testid="readiness-headline"]').text()).toBe('FOUNDATION — 1 blocker · limiting: System Design 42/72')
    expect(wrapper.text()).not.toMatch(/76%/)
    expect(wrapper.find('[data-testid="blockers"]').text()).toContain('G1 System Design 42 < 45')
    expect(wrapper.find('[data-testid="gates"]').text()).toContain('✗ G1 Foundation exit (1)')
  })
})
