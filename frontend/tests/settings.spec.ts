import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../src/api/client'
import { serve } from './helpers'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn() }))
vi.mock('../src/api', () => ({ api }))

import SettingsView from '../src/views/SettingsView.vue'
import DeveloperView from '../src/views/settings/DeveloperView.vue'

const stubs = { RouterLink: RouterLinkStub }

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

const ACTIVE = {
  id: 2, profile_key: 'backend_fullstack_sde2', target_date: '2027-06-28', weekday_budgets: [90, 90, 90, 90, 90, 75, 75],
  weekly_minutes: 600, valid_from: '2026-10-04', valid_to: null, is_active: true, created_at: '2026-10-04T12:00:00Z',
  phase: 'BUILD', weeks_left: '38.0',
}
const SETTINGS = { timezone: 'Asia/Kolkata', display_name: 'Owner' }
const BACKUP = { available: true, warning: false, message: 'Last backup is 2 h old.' }

describe('SettingsView', () => {
  it('creates the first goal with POST when none exists', async () => {
    api.get.mockImplementation((path: string) => {
      if (['/stories', '/projects', '/prompts', '/catalog/skills'].includes(path)) return Promise.resolve({ data: [], meta: {} })
      if (path === '/settings') return Promise.resolve({ data: SETTINGS, meta: {} })
      if (path === '/goals/history') return Promise.resolve({ data: [], meta: { count: 0 } })
      if (path === '/system/backup-status') return Promise.resolve({ data: BACKUP, meta: {} })
      return Promise.reject(new ApiError('NOT_FOUND', 'No active goal', 404))
    })
    api.post.mockResolvedValue({ data: ACTIVE, meta: {} })
    const wrapper = mount(SettingsView, { global: { stubs } })
    await flushPromises()
    expect(wrapper.text()).toContain('Set a target date (optional)')
    await wrapper.find('[data-testid="target-date"]').setValue('2027-06-28')
    await wrapper.find('[data-testid="budget-6"]').setValue('60')
    await wrapper.find('[data-testid="goal-form"]').trigger('submit')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/goals', { target_date: '2027-06-28', weekday_budgets: [90, 90, 90, 90, 90, 75, 60] })
    expect(api.patch).not.toHaveBeenCalled()
  })

  it('patches the active goal and sends only a changed target date', async () => {
    serve(api, {
      '/stories': [], '/projects': [], '/prompts': [], '/catalog/skills': [], '/settings': SETTINGS, '/goals/history': [ACTIVE],
      '/goals/active': ACTIVE, '/system/backup-status': BACKUP,
    })
    api.patch.mockResolvedValue({ data: ACTIVE, meta: {} })
    const wrapper = mount(SettingsView, { global: { stubs } })
    await flushPromises()
    expect(wrapper.find('[data-testid="goal-summary"]').text()).toMatch(/^Building foundations\s*·\s*38 weeks to go\s*·\s*10h a week$/)
    await wrapper.find('[data-testid="budget-0"]').setValue('120')
    await wrapper.find('[data-testid="goal-form"]').trigger('submit')
    await flushPromises()
    expect(api.patch).toHaveBeenCalledWith('/goals/active', { weekday_budgets: [120, 90, 90, 90, 90, 75, 75] })
  })

  it('keeps data safety close, and developer tools one click away rather than inline', async () => {
    serve(api, {
      '/stories': [], '/projects': [], '/prompts': [], '/catalog/skills': [], '/settings': SETTINGS, '/goals/history': [ACTIVE],
      '/goals/active': ACTIVE, '/system/backup-status': { available: true, warning: true, message: 'Last backup is 40 h old.' },
    })
    const wrapper = mount(SettingsView, { global: { stubs } })
    await flushPromises()
    expect(wrapper.find('[data-testid="backup-summary"]').text()).toContain('Last backup is 40 h old.')
    expect(wrapper.find('[data-testid="export-json"]').attributes('href')).toBe('/api/v1/export/json')
    expect(wrapper.find('[data-testid="developer-link"]').text()).toContain('Developer / System')
    expect(wrapper.text()).not.toMatch(/ruleset|seed version|fingerprint/i)
  })
})

describe('DeveloperView', () => {
  it('holds the technical details: health, versions, backups, the catalog link and the reset procedure', async () => {
    serve(api, {
      '/health': { db: 'ok', ruleset_version: 'v1', seed_version: 'seed-v1' },
      '/catalog': { seed_version: 'seed-v1', catalog_fingerprint: 'abc', loaded_at: '2026-10-04T10:00:00Z', versions: {}, files: [], counts: { skills: 133, problems: 44 } },
      '/system/backup-status': { available: true, latest_file: 'mastermentor-20261005T055446Z.sql.gz', taken_at: '2026-10-05T05:54:46Z', age_hours: 1 },
    })
    const wrapper = mount(DeveloperView, { global: { stubs } })
    await vi.waitFor(() => expect(wrapper.find('[data-testid="health"]').exists()).toBe(true))
    await flushPromises()
    const health = wrapper.find('[data-testid="health"]').text()
    expect(health).toContain('Connected')
    expect(health).toContain('v1')
    expect(health).toContain('seed-v1')
    expect(wrapper.find('[data-testid="backup-facts"]').text()).toContain('mastermentor-20261005T055446Z.sql.gz')
    expect(wrapper.find('[data-testid="catalog-link"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('make dev-reset CONFIRM=RESET-PREP-DATA')
  })
})
