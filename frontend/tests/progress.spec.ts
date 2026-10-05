import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { HISTORY, MOCK_SUMMARY, READINESS, revisionItem, revisionList, review, SKILLS } from './fixtures'
import { networkDown, serve } from './helpers'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn() }))
vi.mock('../src/api', () => ({ api }))

import ProgressView from '../src/views/ProgressView.vue'

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

function routes(overrides: Record<string, unknown> = {}) {
  serve(api, {
    '/readiness': READINESS, '/readiness/history': HISTORY, '/revisions': revisionList([revisionItem('CS:a', 'overdue'), revisionItem('CS:b', 'due')]),
    '/mocks/summary': MOCK_SUMMARY, '/weekly-reviews': [review(), { ...review(), id: 2, week_start: '2026-09-21' }], '/skills': SKILLS, ...overrides,
  })
}
async function open() {
  const wrapper = mount(ProgressView, { global: { stubs: { RouterLink: RouterLinkStub } } })
  await vi.waitFor(() => expect(wrapper.find('[data-testid="readiness-headline"]').exists()).toBe(true))
  await flushPromises()
  return wrapper
}

describe('ProgressView', () => {
  it('headlines the readiness in plain words with the trend, never a percentage', async () => {
    routes()
    const wrapper = await open()
    expect(wrapper.find('[data-testid="readiness-headline"]').text()).toBe('Developing')
    expect(wrapper.text()).toContain('Solid progress. A few areas still hold you back.')
    expect(wrapper.text()).toContain('74')
    expect(wrapper.text()).not.toMatch(/74%/)
    expect(wrapper.find('figure.chart').exists()).toBe(true)
  })

  it('says what is holding you back without gate codes', async () => {
    routes()
    const wrapper = await open()
    const blockers = wrapper.find('[data-testid="blockers"]')
    expect(blockers.text()).toContain('System Design 54 < 72')
    expect(blockers.text()).not.toMatch(/\bG\d\b/)
  })

  it('shows growth by area, revision health, mock trend and weekly consistency', async () => {
    routes()
    const wrapper = await open()
    const areas = wrapper.find('[data-testid="areas"]')
    expect(areas.findAll('li')).toHaveLength(3)
    expect(areas.text()).toContain('System Design')
    expect(areas.text()).toContain('54')
    expect(areas.text()).toContain('72 needed')
    expect(wrapper.find('[data-testid="revision-health"]').text()).toContain('1 overdue')
    expect(wrapper.find('[data-testid="revision-health"]').text()).toContain('1 due')
    expect(wrapper.text()).toContain('Mock trend')
    expect(wrapper.findAll('[data-testid="weeks"] li')).toHaveLength(2)
  })

  it('keeps the technical gate list collapsed and under a plain heading', async () => {
    routes()
    const wrapper = await open()
    const details = wrapper.find('details.advanced')
    expect(details.attributes('open')).toBeUndefined()
    expect(details.find('summary').text()).toBe('Readiness checks in detail')
    expect(details.find('[data-testid="gates"]').text()).toContain('Each area at its level')
  })

  it('explains an empty history instead of drawing an empty chart', async () => {
    routes({ '/readiness/history': [HISTORY[0]!], '/weekly-reviews': [] })
    const wrapper = await open()
    expect(wrapper.find('figure.chart').exists()).toBe(false)
    expect(wrapper.text()).toContain('Your trend appears after a second day of history.')
    expect(wrapper.text()).toContain('Your weekly rhythm appears after your first full week.')
  })

  it('shows a calm error with Retry when the engine is unreachable', async () => {
    routes({ '/readiness': networkDown() })
    const wrapper = mount(ProgressView, { global: { stubs: { RouterLink: RouterLinkStub } } })
    await vi.waitFor(() => expect(wrapper.find('[data-testid="error-state"]').exists()).toBe(true))
    expect(wrapper.text()).toContain("Master Mentor can't reach the preparation engine right now.")
  })
})
