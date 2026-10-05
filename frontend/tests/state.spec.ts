import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { currentState, HISTORY, MOCK_SUMMARY, READINESS, review, revisionList, SKILLS } from './fixtures'
import { serve } from './helpers'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn() }))
vi.mock('../src/api', () => ({ api }))

import CurrentState from '../src/components/progress/CurrentState.vue'
import ProgressView from '../src/views/ProgressView.vue'

const stubs = { RouterLink: RouterLinkStub }

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('Your current state', () => {
  it('snapshots what was measured: strong, developing, critical gaps and unknown', () => {
    const wrapper = mount(CurrentState, { global: { stubs }, props: { state: currentState() } })
    expect(wrapper.find('[data-testid="current-state"] h2').text()).toBe('Your current state')
    expect(wrapper.find('[data-testid="state-strong"]').text()).toMatch(/Strong\s*1/)
    expect(wrapper.find('[data-testid="state-strong"]').text()).toContain('Array traversal')
    expect(wrapper.find('[data-testid="state-strong"]').text()).toContain('88 / 80')
    expect(wrapper.find('[data-testid="state-critical"]').text()).toContain('Caching strategies')
    expect(wrapper.find('[data-testid="state-developing"]').text()).toContain('Graphs: BFS and DFS')
    expect(wrapper.find('[data-testid="state-unknown"]').text()).toMatch(/Unknown\s*25/)
    expect(wrapper.text()).toContain('What Master Mentor measured about you so far.')
  })

  it('separates self-reported context with the "not yet verified" label', () => {
    const wrapper = mount(CurrentState, { global: { stubs }, props: { state: currentState() } })
    expect(wrapper.text()).toContain('Self-reported context — not yet verified.')
    expect(wrapper.text()).toContain('Your own assessments never change a score.')
    expect(wrapper.find('[data-testid="self-report-vs-observed"]').exists()).toBe(true)
    const edit = wrapper.findAllComponents(RouterLinkStub).find((c) => c.text().includes('Edit starting profile'))
    expect(edit?.props('to')).toEqual({ name: 'onboarding' })
  })

  it('invites optional context when there is none', () => {
    const wrapper = mount(CurrentState, { global: { stubs }, props: { state: currentState({ self_reported: [] }) } })
    expect(wrapper.find('[data-testid="self-report-vs-observed"]').exists()).toBe(false)
    expect(wrapper.text()).toContain("You haven't added any self-reported context.")
  })

  it('appears on the Progress page, above the trend and blockers', async () => {
    serve(api, {
      '/readiness': READINESS, '/readiness/history': HISTORY, '/revisions': revisionList([]), '/mocks/summary': MOCK_SUMMARY,
      '/weekly-reviews': [review()], '/skills': SKILLS, '/profile/state': currentState(),
    })
    const wrapper = mount(ProgressView, { global: { stubs } })
    await vi.waitFor(() => expect(wrapper.find('[data-testid="current-state"]').exists()).toBe(true))
    await flushPromises()
    const html = wrapper.html()
    expect(html.indexOf('data-testid="current-state"')).toBeLessThan(html.indexOf('data-testid="blockers"'))
  })
})
