import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { MockRecord } from '../src/api/types'
import { emptyRound, mockErrors } from '../src/practice/mock'
import { EMPTY_MOCK_SUMMARY, MOCK_SUMMARY, SKILLS } from './fixtures'
import { serve } from './helpers'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn() }))
const route = vi.hoisted(() => ({ query: {} as Record<string, string> }))
vi.mock('../src/api', () => ({ api }))
vi.mock('vue-router', async (orig) => ({ ...(await orig<object>()), useRoute: () => route }))

import MocksView from '../src/views/MocksView.vue'

const CATALOG = [{ key: 'sd.caching', component: 'system_design' }, { key: 'db.indexing', component: 'cs' }]
const MOCK: MockRecord = {
  id: 1, occurred_on: '2026-10-01', source: 'PEER', is_final_simulation: false, is_current: true,
  rounds: [{ id: 1, position: 1, round_type: 'DSA', duration_minutes: 45, round_score: 78, skills: [] }],
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  route.query = {}
  api.post.mockResolvedValue({ data: {}, meta: {}, effects: { run_id: 1, skill_deltas: [] } })
})

function routes(summary = MOCK_SUMMARY, mocks: MockRecord[] = [MOCK]) {
  serve(api, { '/mocks/summary': summary, '/mocks': mocks, '/catalog/skills': CATALOG, '/skills': SKILLS })
}

async function open() {
  const wrapper = mount(MocksView, { global: { stubs: { RouterLink: RouterLinkStub } } })
  await vi.waitFor(() => expect(wrapper.find('[data-testid="mock-types"]').exists() || wrapper.find('[data-testid="empty-state"]').exists()).toBe(true))
  await flushPromises()
  return wrapper
}

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
  it('invites a first mock when there are none, in the mentor\'s words', async () => {
    routes(EMPTY_MOCK_SUMMARY, [])
    const wrapper = await open()
    const empty = wrapper.find('[data-testid="empty-state"]')
    expect(empty.text()).toContain("You haven't completed a mock interview yet.")
    expect(empty.text()).toContain('Master Mentor will use your mock results to identify interview-execution gaps.')
    await empty.find('[data-testid="first-mock"]').trigger('click')
    expect(wrapper.find('[data-testid="mock-form"]').exists()).toBe(true)
  })

  it('shows the next mock, scores per round type, the diagnosis and recent mocks', async () => {
    routes()
    const wrapper = await open()
    expect(wrapper.find('[data-testid="next-mock"]').text()).toContain('DSA round')
    expect(wrapper.find('[data-testid="next-mock"]').text()).toContain('1 of 3 done in the last 60 days.')
    const types = wrapper.find('[data-testid="mock-types"]').text()
    expect(types).toContain('DSA')
    expect(types).toContain('78')
    expect(types).toContain('System design')
    expect(types).toContain('62')
    const diagnosis = wrapper.find('.diagnosis').text()
    expect(diagnosis).toContain('Your repeated weakness:')
    expect(diagnosis).toContain('Caching strategies')
    expect(diagnosis).toContain('It came up in 2 mock rounds.')
    expect(wrapper.text()).toContain('Recent mocks')
    expect(wrapper.text()).toContain('With a peer')
    expect(wrapper.text()).not.toMatch(/G6|g6|SYSTEM_DESIGN latest/)
  })

  it('offers only skills of the round type when logging', async () => {
    routes()
    const wrapper = await open()
    await wrapper.find('[data-testid="log-mock"]').trigger('click')
    await flushPromises()
    await wrapper.find('[data-testid="round-0-type"]').setValue('SYSTEM_DESIGN')
    const options = wrapper.find('[data-testid="round-0-skill"]').findAll('option').map((o) => o.text())
    expect(options).toEqual(['Choose…', 'Caching strategies'])
  })

  it('posts the mock, or completes the plan item when opened from Today', async () => {
    route.query = { plan_item: '42' }
    routes()
    const wrapper = await open()
    expect(wrapper.find('[data-testid="mock-form"]').exists()).toBe(true)
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
    await vi.waitFor(() => expect(wrapper.find('[data-testid="effects-panel"]').exists()).toBe(true))
  })
})
