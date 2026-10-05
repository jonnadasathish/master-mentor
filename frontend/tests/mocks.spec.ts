import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { emptyRound, mockErrors } from '../src/practice/mock'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn() }))
const route = vi.hoisted(() => ({ query: {} as Record<string, string> }))
vi.mock('../src/api', () => ({ api }))
vi.mock('vue-router', async (orig) => ({ ...(await orig<object>()), useRoute: () => route }))

import MocksView from '../src/views/mocks/MocksView.vue'

const SUMMARY = {
  as_of_date: '2026-11-02', by_type: [{ round_type: 'SYSTEM_DESIGN', rounds_60d: 1, required_60d: 2, non_self_60d: 1,
    latest: { date: '2026-11-01', score: 58 }, trend: [{ date: '2026-11-01', score: 58 }], g6_failing: ['SYSTEM_DESIGN latest round 58 < 65'] }],
  g6_passed: false, repeated_weaknesses: [['sd.caching', 2]], final_simulations: [], g9_passed: false,
  g9_failing: ['0 of 3 final simulations'], simulation_eligible: false,
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  route.query = {}
  api.get.mockImplementation((path: string) =>
    Promise.resolve({ data: path === '/mocks/summary' ? SUMMARY : path === '/catalog/skills' ? [{ key: 'sd.caching', component: 'system_design' }, { key: 'db.indexing', component: 'cs' }] : [], meta: {} }),
  )
  api.post.mockResolvedValue({ data: {}, meta: {}, effects: { run_id: 1, skill_deltas: [] } })
})

describe('mock form helpers', () => {
  it('validates scores, durations and duplicate skills', () => {
    const r = emptyRound('SYSTEM_DESIGN')
    expect(mockErrors([r])).toEqual([])
    r.round_score = 120
    r.skills = [{ skill: 'a', outcome_points: 50, is_weakness: false }, { skill: 'a', outcome_points: 60, is_weakness: false }]
    expect(mockErrors([r])).toEqual(['Round 1: score 0–100.', 'Round 1: a skill is listed twice.'])
    expect(mockErrors([])).toEqual(['Add at least one round.'])
  })
})

describe('MocksView', () => {
  it('shows G6 per type, repeated weaknesses and offers only skills of the round type', async () => {
    const wrapper = mount(MocksView, { global: { stubs: { RouterLink: RouterLinkStub } } })
    await flushPromises()
    expect(wrapper.find('[data-testid="mock-types"]').text()).toContain('✗ SYSTEM_DESIGN latest round 58 < 65')
    expect(wrapper.text()).toContain('sd.caching — flagged in 2 rounds')
    await wrapper.find('[data-testid="round-0-type"]').setValue('SYSTEM_DESIGN')
    const options = wrapper.find('[data-testid="round-0-skill"]').findAll('option').map((o) => o.text())
    expect(options).toEqual(['Choose…', 'sd.caching'])
  })

  it('posts the mock, or completes the plan item when opened from Today', async () => {
    route.query = { plan_item: '42' }
    const wrapper = mount(MocksView, { global: { stubs: { RouterLink: RouterLinkStub } } })
    await flushPromises()
    await wrapper.find('[data-testid="round-0-type"]').setValue('SYSTEM_DESIGN')
    await wrapper.find('[data-testid="round-0-skill"]').setValue('sd.caching')
    await wrapper.find('[data-testid="round-0-add-skill"]').trigger('click')
    await wrapper.find('[data-testid="round-0-weak-sd.caching"]').setValue(true)
    await wrapper.find('[data-testid="mock-form"]').trigger('submit')
    await flushPromises()
    const [path, body] = api.post.mock.calls[0]!
    expect(path).toBe('/plan/items/42/complete')
    expect(body).toMatchObject({ observation: { type: 'MOCK', body: { source: 'PEER', rounds: [{ round_type: 'SYSTEM_DESIGN',
      skills: [{ skill: 'sd.caching', outcome_points: 60, is_weakness: true }] }] } } })
    expect(wrapper.find('[data-testid="effects-panel"]').exists()).toBe(true)
  })
})
