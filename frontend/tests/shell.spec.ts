import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import { createMemoryHistory } from 'vue-router'
import ErrorBoundary from '../src/components/common/ErrorBoundary.vue'
import MobileNav from '../src/components/shell/MobileNav.vue'
import { createAppRouter } from '../src/router'
import { NAV_ITEMS } from '../src/router/nav'
import { useErrorStore } from '../src/stores/errors'
import { calibrationToday, baselineIn, FIRST_RUN_PROFILE, PROFILE, SKILLS, READINESS, HISTORY, WEEK } from './fixtures'
import { serve } from './helpers'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn() }))
vi.mock('../src/api', () => ({ api }))

import App from '../src/App.vue'

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  localStorage.clear()
})

describe('navigation', () => {
  beforeEach(() => serve(api, { '/profile': PROFILE }))
  it('has the focused primary navigation and no developer tools in it', () => {
    expect(NAV_ITEMS.map((i) => i.label)).toEqual(['Today', 'Prepare', 'Revise', 'Mocks', 'Progress', 'Roadmap', 'Settings'])
    expect(NAV_ITEMS.find((i) => i.key === 'prepare')?.children?.map((c) => c.label)).toEqual([
      'DSA', 'CS Fundamentals', 'System Design', 'LLD / OOD', 'Behavioral',
    ])
    const everyLabel = JSON.stringify(NAV_ITEMS).toLowerCase()
    for (const internal of ['catalog', 'status', 'health', 'diagnostic', 'seed', 'audit']) expect(everyLabel).not.toContain(internal)
  })

  it('opens Today at the root and keeps technical pages under Settings → Developer', async () => {
    const router = createAppRouter(createMemoryHistory())
    await router.push('/')
    expect(router.currentRoute.value.name).toBe('today')
    expect(router.resolve('/settings/developer').name).toBe('developer')
    expect(router.resolve('/settings/developer/catalog').name).toBe('catalog')
    await router.push('/status')
    expect(router.currentRoute.value.path).toBe('/settings/developer')
    await router.push('/catalog')
    expect(router.currentRoute.value.path).toBe('/settings/developer/catalog')
  })

  it('keeps old addresses working', async () => {
    const router = createAppRouter(createMemoryHistory())
    for (const [from, to] of [['/skills', '/prepare'], ['/revision', '/revise'], ['/log/problems', '/prepare/dsa/problems'], ['/nope/deep', '/']]) {
      await router.push(from!)
      expect(router.currentRoute.value.path).toBe(to)
    }
  })
})

describe('first-run guard', () => {
  it('sends every page to the onboarding until the starting profile is completed', async () => {
    serve(api, { '/profile': FIRST_RUN_PROFILE })
    const router = createAppRouter(createMemoryHistory())
    for (const path of ['/', '/prepare', '/roadmap', '/calibrate']) {
      await router.push(path)
      expect(router.currentRoute.value.name, path).toBe('onboarding')
    }
    await router.push('/settings/developer')
    expect(router.currentRoute.value.name).toBe('developer') // developer tools stay reachable
  })

  it('lets a completed profile through to Today', async () => {
    serve(api, { '/profile': PROFILE })
    const router = createAppRouter(createMemoryHistory())
    await router.push('/')
    expect(router.currentRoute.value.name).toBe('today')
  })

  it('never blocks navigation when the profile cannot be read', async () => {
    serve(api, {})
    const router = createAppRouter(createMemoryHistory())
    await router.push('/prepare')
    expect(router.currentRoute.value.name).toBe('prepare')
  })
})

describe('app shell', () => {
  async function mountAt(path: string) {
    serve(api, {
      '/today': calibrationToday(0), '/baseline': baselineIn('NOT_STARTED'), '/profile': PROFILE, '/skills': SKILLS, '/readiness': READINESS,
      '/readiness/history': HISTORY, '/settings': { timezone: 'Asia/Kolkata', display_name: 'Satish' }, '/today/week': WEEK,
      '/system/backup-status': { warning: false, message: 'ok' },
    })
    const router = createAppRouter(createMemoryHistory())
    await router.push(path)
    await router.isReady()
    const wrapper = mount(App, { global: { plugins: [router] } })
    await vi.waitFor(() => expect(wrapper.find('h1').exists()).toBe(true))
    await flushPromises()
    return { wrapper, router }
  }

  it('root route renders the Today experience with Today marked as the current page', async () => {
    const { wrapper } = await mountAt('/')
    expect(wrapper.find('[data-testid="today-header"]').text()).toContain('Today')
    const today = wrapper.find('[data-testid="nav-today"]')
    expect(today.attributes('aria-current')).toBe('page')
    expect(wrapper.find('nav[aria-label="Main"]').exists()).toBe(true)
    expect(wrapper.text()).not.toMatch(/catalog|ruleset|seed/i)
  })

  it('expands the Prepare group only inside Prepare and shows the Log practice action', async () => {
    const { wrapper } = await mountAt('/prepare/dsa')
    expect(wrapper.find('[data-testid="nav-dsa"]').classes()).toContain('active')
    expect(wrapper.find('[data-testid="nav-cs"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="log-practice"]').exists()).toBe(true)
  })
})

describe('mobile navigation', () => {
  it('shows the four daily destinations and tucks the rest behind More', async () => {
    const router = createAppRouter(createMemoryHistory())
    await router.push('/')
    const wrapper = mount(MobileNav, { global: { plugins: [router] } })
    expect(wrapper.findAll('.tab-item').map((n) => n.text())).toEqual(['Today', 'Prepare', 'Revise', 'Mocks', 'More'])
    expect(wrapper.find('[data-testid="more-menu"]').exists()).toBe(false)
    await wrapper.find('[data-testid="mobile-nav-more"]').trigger('click')
    const menu = wrapper.find('[data-testid="more-menu"]')
    expect(menu.text()).toContain('Progress')
    expect(menu.text()).toContain('Roadmap')
    expect(menu.text()).toContain('Settings')
    expect(menu.text()).toContain('Log practice')
    expect(wrapper.find('[data-testid="mobile-nav-more"]').attributes('aria-expanded')).toBe('true')
  })
})

describe('ErrorBoundary', () => {
  it('renders a calm fallback and reports when a child throws', async () => {
    const Broken = defineComponent({
      setup() {
        throw new Error('render exploded')
      },
      render: () => null,
    })
    const wrapper = mount(ErrorBoundary, { slots: { default: () => h(Broken) } })
    await nextTick()
    expect(wrapper.find('[data-testid="error-fallback"]').text()).toContain("This page couldn't be shown.")
    expect(useErrorStore().errors[0]).toMatchObject({ code: 'UI_ERROR', message: 'render exploded', source: 'component' })
  })

  it('renders children when nothing fails', () => {
    const wrapper = mount(ErrorBoundary, { slots: { default: () => h('p', 'fine') } })
    expect(wrapper.text()).toBe('fine')
  })
})
