import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory } from 'vue-router'
import type { CalibrationPhase, PlanItem } from '../src/api/types'
import { createAppRouter } from '../src/router'
import { baselineIn, baselineItem, calibrationToday, currentState, HISTORY, PROFILE, READINESS, SKILLS, WEEK } from './fixtures'
import { serve } from './helpers'

/**
 * Regression tests for "Continue calibration does not enter the calibration flow". They use the real application router
 * (memory history), the real route guard and the real App shell, so a navigation or guard bug cannot hide behind a mock.
 */
const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn() }))
vi.mock('../src/api', () => ({ api }))

import App from '../src/App.vue'

const DONE = { status: 'DONE' as const, completed_at: '2026-10-05T08:00:00Z' }
const diagnosticA = (extra: Partial<PlanItem> = {}) => baselineItem({ id: 9, position: 1, battery_item_key: 'M0-B02', minutes: 60, ...extra })
const pythonWarmup = (extra: Partial<PlanItem> = {}) => baselineItem({ id: 10, position: 2, battery_item_key: 'M0-B03', minutes: 30, ...extra })

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  localStorage.clear()
  api.post.mockResolvedValue({ data: {}, meta: {} })
})

async function boot(path: string, phase: CalibrationPhase, items: PlanItem[]) {
  serve(api, {
    '/today': phase === 'COMPLETE' ? { ...calibrationToday(12, items), calibration: { ...calibrationToday(12).calibration, active: false } } : calibrationToday(phase === 'NOT_STARTED' ? 0 : 2, items),
    '/baseline': baselineIn(phase), '/profile': PROFILE, '/skills': SKILLS, '/readiness': READINESS, '/readiness/history': HISTORY,
    '/today/week': WEEK, '/profile/state': currentState(), '/system/backup-status': { warning: false, message: 'ok' },
    '/settings': { timezone: 'Asia/Kolkata', display_name: 'Satish' },
  })
  const router = createAppRouter(createMemoryHistory())
  await router.push(path)
  await router.isReady()
  const wrapper = mount(App, { global: { plugins: [router] }, attachTo: document.body })
  await vi.waitFor(() => expect(wrapper.find('h1').exists()).toBe(true))
  await flushPromises()
  return { wrapper, router }
}

describe('Continue calibration flow (real router)', () => {
  it('1. in progress: clicking Continue calibration on Today navigates, through the router, to /calibrate', async () => {
    const { wrapper, router } = await boot('/', 'IN_PROGRESS', [diagnosticA(DONE), pythonWarmup()])
    expect(router.currentRoute.value.name).toBe('today')
    const button = wrapper.find('[data-testid="continue-calibration"]')
    expect(button.attributes('href')).toContain('/calibrate')
    await button.trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/calibrate'))
    await vi.waitFor(() => expect(wrapper.find('h1').text()).toBe('Calibrate your skills'))
    wrapper.unmount()
  })

  it('2. in progress: /calibrate loads the hub and is never redirected to Today', async () => {
    const { wrapper, router } = await boot('/calibrate', 'IN_PROGRESS', [diagnosticA(DONE), pythonWarmup()])
    expect(router.currentRoute.value.name).toBe('calibrate')
    expect(wrapper.find('h1').text()).toBe('Calibrate your skills')
    expect(wrapper.find('[data-testid="calibration-cta"]').attributes('data-phase')).toBe('IN_PROGRESS')
    expect(wrapper.find('[data-testid="plan-items"]').exists()).toBe(true)
    expect(api.post).not.toHaveBeenCalled() // opening the hub alone starts nothing
    wrapper.unmount()
  })

  it('3. a pending diagnostic: Continue opens exactly that task, and never restarts the finished one', async () => {
    const { wrapper, router } = await boot('/', 'IN_PROGRESS', [diagnosticA(DONE), pythonWarmup()])
    await wrapper.find('[data-testid="continue-calibration"]').trigger('click')
    await vi.waitFor(() => expect(api.post).toHaveBeenCalledWith('/plan/items/10/start', {}))
    expect(api.post).toHaveBeenCalledTimes(1)
    expect(router.currentRoute.value.path).toBe('/calibrate')
    await vi.waitFor(() => expect(wrapper.find('[data-testid="plan-item-2"]').attributes('data-phase')).toBe('in-progress'))
    expect(wrapper.find('[data-testid="plan-item-1"]').attributes('data-phase')).toBe('completed')

    // Continuing again resumes the task in progress instead of starting anything else.
    await wrapper.find('[data-testid="continue-calibration"]').trigger('click')
    await flushPromises()
    expect(api.post).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })

  it('4. every assessment scheduled for today is done: the hub says so, starts nothing and invents nothing', async () => {
    const { wrapper, router } = await boot('/', 'IN_PROGRESS', [diagnosticA(DONE), pythonWarmup(DONE)])
    await wrapper.find('[data-testid="continue-calibration"]').trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/calibrate'))
    await vi.waitFor(() => expect(wrapper.find('[data-testid="today-done"]').exists()).toBe(true))
    const notice = wrapper.find('[data-testid="today-done"]').text()
    expect(notice).toContain("You've finished today's calibration work.")
    expect(notice).toContain('Next assessment: CS quiz') // M0-B04, the first battery item not yet complete or scheduled
    expect(api.post).not.toHaveBeenCalled()
    expect(wrapper.findAll('[data-phase="not-started"]')).toHaveLength(0)
    expect(wrapper.find('[data-testid="no-work-today"]').exists()).toBe(false)
    wrapper.unmount()
  })

  it('4b. a mission whose assessment is already complete is never offered or started again', async () => {
    // The familiarity sweep (M0-B01) is recorded on its own page: the battery item is complete while its plan item is still pending.
    const sweep = baselineItem({ id: 8, position: 1, battery_item_key: 'M0-B01', minutes: 15, started_at: '2026-10-05T07:00:00Z' })
    const { wrapper } = await boot('/calibrate', 'IN_PROGRESS', [sweep, pythonWarmup()])
    expect(wrapper.find('[data-testid="plan-item-1"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="completed-assessments"]').text()).toContain('Familiarity sweep')
    await wrapper.find('[data-testid="continue-calibration"]').trigger('click')
    await vi.waitFor(() => expect(api.post).toHaveBeenCalledWith('/plan/items/10/start', {}))
    expect(api.post).not.toHaveBeenCalledWith('/plan/items/8/start', {})
    wrapper.unmount()
  })

  it('5. the first-run guard lets a user with a completed profile stay on /calibrate, with or without ?start=1', async () => {
    for (const path of ['/calibrate', '/calibrate?start=1']) {
      setActivePinia(createPinia())
      const { wrapper, router } = await boot(path, 'IN_PROGRESS', [diagnosticA(DONE), pythonWarmup()])
      expect(router.currentRoute.value.name, path).toBe('calibrate')
      expect(router.currentRoute.value.path, path).toBe('/calibrate')
      wrapper.unmount()
    }
  })

  it('6. NOT_STARTED: Start calibration also reaches the hub and starts the first scheduled task', async () => {
    const { wrapper, router } = await boot('/', 'NOT_STARTED', [diagnosticA()])
    await wrapper.find('[data-testid="continue-calibration"]').trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/calibrate'))
    await vi.waitFor(() => expect(api.post).toHaveBeenCalledWith('/plan/items/9/start', {}))
    wrapper.unmount()
  })

  it('7. COMPLETE: /calibrate shows the results, not a redirect and not a Continue button', async () => {
    const { wrapper, router } = await boot('/calibrate', 'COMPLETE', [])
    expect(router.currentRoute.value.name).toBe('calibrate')
    expect(wrapper.find('[data-testid="baseline-summary"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="continue-calibration"]').exists()).toBe(false)
    wrapper.unmount()
  })
})
