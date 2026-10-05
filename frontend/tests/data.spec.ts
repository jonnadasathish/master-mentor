import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn() }))
vi.mock('../src/api', () => ({ api }))

import BackupBanner from '../src/components/settings/BackupBanner.vue'
import ImportPanel from '../src/components/settings/ImportPanel.vue'

beforeEach(() => vi.clearAllMocks())

describe('BackupBanner', () => {
  it('warns only when the server says the backup is stale', async () => {
    api.get.mockResolvedValue({ data: { warning: true, message: 'Last backup is 40 h old.' }, meta: {} })
    const stale = mount(BackupBanner)
    await flushPromises()
    expect(stale.find('[data-testid="backup-warning"]').text()).toContain('Last backup is 40 h old.')
    api.get.mockResolvedValue({ data: { warning: false, message: 'Last backup is 2 h old.' }, meta: {} })
    const fresh = mount(BackupBanner)
    await flushPromises()
    expect(fresh.find('[data-testid="backup-warning"]').exists()).toBe(false)
  })
})

describe('ImportPanel', () => {
  it('previews, requires the exact confirmation phrase, then commits', async () => {
    const doc = { format: 'master-mentor-export', format_version: 2, tables: {} }
    api.post.mockImplementation((path: string) => Promise.resolve(path === '/import/preview'
      ? { data: { ok: true, errors: [], warnings: [], counts: { problem_attempts: 2 }, confirmation: 'IMPORT-INTO-EMPTY-DATABASE', exported_at: null }, meta: {} }
      : { data: { inserted: { problem_attempts: 2, assessments: 1 } }, meta: {} }))
    const wrapper = mount(ImportPanel)
    const input = wrapper.find('[data-testid="import-file"]')
    const file = new File([JSON.stringify(doc)], 'export.json', { type: 'application/json' })
    Object.defineProperty(input.element, 'files', { value: [file] })
    await input.trigger('change')
    await vi.waitFor(async () => {
      await flushPromises()
      expect(wrapper.find('[data-testid="import-counts"]').exists()).toBe(true)
    })
    expect(wrapper.find('[data-testid="import-counts"]').text()).toContain('problem_attempts: 2')
    const button = wrapper.find('[data-testid="import-commit"]')
    expect((button.element as HTMLButtonElement).disabled).toBe(true)
    await wrapper.find('[data-testid="import-confirm"]').setValue('IMPORT-INTO-EMPTY-DATABASE')
    await button.trigger('click')
    await flushPromises()
    expect(api.post).toHaveBeenLastCalledWith('/import/commit', { document: doc, confirm: 'IMPORT-INTO-EMPTY-DATABASE' })
    expect(wrapper.text()).toContain('Imported 3 rows; derived state rebuilt.')
  })
})
