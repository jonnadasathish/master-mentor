import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ApiClient } from '../src/api/client'
import AttemptForm from '../src/components/AttemptForm.vue'
import { buildAssessmentPayload, emptyAssessmentForm } from '../src/practice/assessment'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn() }))
vi.mock('../src/api', () => ({ api }))

import RevisionView from '../src/views/revision/RevisionView.vue'

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

const item = (key: string, bucket: string, extra: Record<string, unknown> = {}) => ({
  item_key: key, item_type: key.split(':')[0], skill: 'db.indexing', skill_name: 'Indexing', tier: 'T1', importance: 100,
  parked: false, state: 'ACTIVE', suspend_reason: null, interval_index: 0, due_date: '2026-10-01', days_overdue: 3,
  lapses: 1, needs_reinforcement: true, minutes: 20, bucket, review_kind: 'CONCEPT_EXPLAIN', subject_ref: 'db.indexing',
  last_reviewed_on: null, ...extra,
})

describe('RevisionView', () => {
  it('opens on the first non-empty bucket, links problem reviews and posts manual actions', async () => {
    api.get.mockResolvedValue({
      data: {
        backlog_minutes: 45, cap_minutes: 36, triage_threshold_minutes: 504,
        counts: { overdue: 0, due: 2, upcoming: 0, maintenance: 0, suspended: 0, graduated: 0 },
        items: [item('CS:db.indexing', 'due'), item('PROBLEM:27', 'due', { subject_ref: '27', review_kind: 'ATTEMPT', minutes: 25 })],
      },
      meta: { run_id: 4 },
    })
    api.post.mockResolvedValue({ data: {}, meta: {} })
    const wrapper = mount(RevisionView, { global: { stubs: { RouterLink: RouterLinkStub } } })
    await flushPromises()
    expect(wrapper.find('[data-testid="backlog"]').text()).toContain('Backlog 45 min · daily cap 36 min')
    expect(wrapper.find('[data-testid="bucket-due"]').attributes('aria-pressed')).toBe('true')
    const link = wrapper.findAllComponents(RouterLinkStub).find((c) => c.attributes('data-testid') === 'review-PROBLEM:27')
    expect(link?.props('to')).toEqual({ name: 'problem', params: { problemKey: '27' }, query: { revision: 'PROBLEM:27' } })
    await wrapper.find('[data-testid="suspend-CS:db.indexing"]').trigger('click')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/revisions/CS%3Adb.indexing/suspend', {})
    await wrapper.find('[data-testid="review-CS:db.indexing"]').trigger('click')
    expect(wrapper.find('[data-testid="assessment-form"]').exists()).toBe(true)
  })
})

describe('review linking', () => {
  it('assessment payload carries the revision key and REVISION mode', () => {
    const form = emptyAssessmentForm('revision:CS:db.indexing', ['db.indexing'])
    form.points['db.indexing'] = 80
    expect(buildAssessmentPayload('CONCEPT_EXPLAIN', form, 'r-12345678', undefined, 'CS:db.indexing')).toMatchObject({
      revision_item_key: 'CS:db.indexing', mode: 'REVISION',
    })
  })

  it('attempt form posts revision_item_key with mode REVISION', async () => {
    const post = vi.fn().mockResolvedValue({ data: { id: 9 }, meta: {}, effects: { run_id: 1, skill_deltas: [] } })
    const client: ApiClient = { get: vi.fn() as ApiClient['get'], post }
    const wrapper = mount(AttemptForm, {
      global: { stubs: { RouterLink: RouterLinkStub } },
      props: { problemId: 27, client, revisionItemKey: 'PROBLEM:27' },
    })
    await wrapper.find('[data-testid="log-direct"]').trigger('click')
    await wrapper.find('[data-testid="outcome-PASS"]').setValue(true)
    await wrapper.find('[data-testid="minutes"]').setValue('20')
    await wrapper.find('[data-testid="log-form"]').trigger('submit')
    await flushPromises()
    expect(post.mock.calls[0]![1]).toMatchObject({ problem_id: 27, revision_item_key: 'PROBLEM:27', mode: 'REVISION' })
  })
})
