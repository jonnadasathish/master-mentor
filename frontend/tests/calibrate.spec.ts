import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { CalibrationPhase } from '../src/api/types'
import { baselineIn, baselineItem, calibrationToday, currentState, HISTORY, PROFILE, READINESS, SKILLS, WEEK } from './fixtures'
import { serve } from './helpers'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn() }))
const route = vi.hoisted(() => ({ query: {} as Record<string, string> }))
vi.mock('../src/api', () => ({ api }))
vi.mock('vue-router', async (orig) => ({ ...(await orig<object>()), useRoute: () => route }))

import CalibrateView from '../src/views/CalibrateView.vue'

const stubs = { RouterLink: RouterLinkStub }

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  route.query = {}
  api.post.mockResolvedValue({ data: {}, meta: {} })
})

async function open(phase: CalibrationPhase, items = [baselineItem({ battery_item_key: 'M0-B03', minutes: 30 })]) {
  serve(api, {
    '/today': calibrationToday(phase === 'NOT_STARTED' ? 0 : 2, items), '/baseline': baselineIn(phase), '/skills': SKILLS, '/profile': PROFILE,
    '/today/week': WEEK, '/readiness': READINESS, '/readiness/history': HISTORY, '/profile/state': currentState(),
  })
  const wrapper = mount(CalibrateView, { global: { stubs } })
  await vi.waitFor(() => expect(wrapper.find('[data-testid="calibration-cta"]').exists()).toBe(true))
  await flushPromises()
  return wrapper
}

describe('Calibration hub', () => {
  it('NOT_STARTED: explains the start and offers "Start calibration"', async () => {
    const wrapper = await open('NOT_STARTED')
    expect(wrapper.find('h1').text()).toBe('Calibrate your skills')
    const cta = wrapper.find('[data-testid="calibration-cta"]')
    expect(cta.attributes('data-phase')).toBe('NOT_STARTED')
    expect(cta.find('[data-testid="continue-calibration"]').text()).toContain('Start calibration')
    expect(wrapper.find('[data-testid="view-roadmap"]').exists()).toBe(false)
  })

  it('IN_PROGRESS: shows progress, time left, the target timeline and "Continue calibration"', async () => {
    const wrapper = await open('IN_PROGRESS')
    const cta = wrapper.find('[data-testid="calibration-cta"]')
    expect(cta.text()).toContain("We've measured 8 of 123 required skills.")
    expect(cta.find('[data-testid="continue-calibration"]').text()).toContain('Continue calibration')
    const progress = wrapper.find('[data-testid="calibration-progress"]').text()
    expect(progress).toContain('2 / 12')
    expect(progress).toContain('8 / 123')
    expect(wrapper.find('[data-testid="calibration-effort"]').text()).toContain('About 5h 50m of assessments left, roughly 5 days at your usual daily time.')
    expect(wrapper.find('[data-testid="calibration-effort"]').text()).toContain('spreads it across your normal preparation time, not in one sitting')
    expect(wrapper.find('[data-testid="calibration-timeline"]').text()).toMatch(/Interview target\s*June 2027/)
    expect(wrapper.findAll('[role="progressbar"]').map((b) => b.attributes('aria-label'))).toEqual(['Baseline assessments completed', 'Required skills measured'])
  })

  it('shows only the calibration work the mentor actually scheduled, with friendly names', async () => {
    const wrapper = await open('IN_PROGRESS')
    expect(wrapper.find('h2#work-title, [id="work-title"]').text()).toBe("Today's calibration work")
    const card = wrapper.find('[data-testid^="plan-item-"]')
    expect(card.text()).toContain('Python warm-up')
    expect(card.text()).toContain('30 min')
    expect(wrapper.text()).not.toMatch(/M0-B\d\d/)
    expect(wrapper.find('[data-testid="completed-assessments"]').text()).toContain('Familiarity sweep')
    expect(wrapper.find('[data-testid="completed-assessments"]').text()).toContain('DSA diagnostic A')
  })

  it('"Continue calibration" starts the next task; so does arriving with ?start=1', async () => {
    const wrapper = await open('IN_PROGRESS')
    await wrapper.find('[data-testid="continue-calibration"]').trigger('click')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/plan/items/10/start', {})

    api.post.mockClear()
    route.query = { start: '1' }
    await open('IN_PROGRESS')
    expect(api.post).toHaveBeenCalledWith('/plan/items/10/start', {})
  })

  it('says so when no calibration work is scheduled for the rest of the day', async () => {
    const wrapper = await open('IN_PROGRESS', [])
    expect(wrapper.find('[data-testid="no-work-today"]').text()).toContain('Pick it up tomorrow')
  })

  it('ENOUGH_MEASURED: offers the roadmap first and still lets you continue', async () => {
    const wrapper = await open('ENOUGH_MEASURED')
    expect(wrapper.find('[data-testid="calibration-cta"]').text()).toContain('We have enough evidence to build your initial roadmap.')
    const roadmap = wrapper.findAllComponents(RouterLinkStub).find((c) => c.attributes('data-testid') === 'view-roadmap')
    expect(roadmap?.props('to')).toEqual({ name: 'roadmap' })
    expect(wrapper.find('[data-testid="continue-calibration"]').text()).toContain('Continue calibration')
  })

  it('COMPLETE: "Baseline complete." with what was found and the roadmap, no more tasks', async () => {
    const wrapper = await open('COMPLETE')
    expect(wrapper.find('[data-testid="calibration-cta"]').text()).toContain('Baseline complete.')
    expect(wrapper.find('[data-testid="continue-calibration"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="view-roadmap"]').exists()).toBe(true)
    const found = wrapper.find('[data-testid="baseline-summary"]').text()
    expect(found).toContain('Array traversal')
    expect(found).toContain('Caching strategies')
    expect(found).toMatch(/25\s*skills have no evidence yet/)
    expect(wrapper.find('[id="work-title"]').exists()).toBe(false)
  })

  it('explains what calibration does', async () => {
    const wrapper = await open('IN_PROGRESS')
    const text = wrapper.find('[data-testid="what-calibration-means"]').text()
    expect(text).toContain('Every task becomes evidence.')
    expect(text).toContain('There is no pass or fail.')
  })
})
