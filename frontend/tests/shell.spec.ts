import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { createMemoryHistory } from 'vue-router'
import { defineComponent, h, nextTick } from 'vue'
import ErrorBoundary from '../src/components/ErrorBoundary.vue'
import { createAppRouter, NAV_ROUTES } from '../src/router'
import { useErrorStore } from '../src/stores/errors'

beforeEach(() => setActivePinia(createPinia()))

describe('router', () => {
  it('has exactly the 7 UI_SPEC pages plus internal status and catalog pages', () => {
    expect(NAV_ROUTES.map((r) => r.name)).toEqual(['today', 'log', 'skills', 'revision', 'mocks', 'progress', 'settings'])
    const router = createAppRouter(createMemoryHistory())
    expect(router.hasRoute('status')).toBe(true)
    expect(router.hasRoute('catalog')).toBe(true)
  })

  it('redirects unknown paths to Today', async () => {
    const router = createAppRouter(createMemoryHistory())
    await router.push('/nope/deep')
    expect(router.currentRoute.value.name).toBe('today')
  })
})

describe('ErrorBoundary', () => {
  it('renders a fallback and reports when a child throws', async () => {
    const Broken = defineComponent({
      setup() {
        throw new Error('render exploded')
      },
      render: () => null,
    })
    const wrapper = mount(ErrorBoundary, { slots: { default: () => h(Broken) } })
    await nextTick() // the boundary re-renders with its fallback on the next tick

    expect(wrapper.find('[data-testid="error-fallback"]').exists()).toBe(true)
    expect(useErrorStore().errors[0]).toMatchObject({ code: 'UI_ERROR', message: 'render exploded', source: 'component' })
  })

  it('renders children when nothing fails', () => {
    const wrapper = mount(ErrorBoundary, { slots: { default: () => h('p', 'fine') } })
    expect(wrapper.text()).toBe('fine')
  })
})
