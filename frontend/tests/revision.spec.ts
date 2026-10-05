import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ApiClient } from '../src/api/client'
import AttemptForm from '../src/components/practice/AttemptForm.vue'
import { buildAssessmentPayload, emptyAssessmentForm } from '../src/practice/assessment'
import { revisionItem, revisionList, SKILLS } from './fixtures'
import { serve } from './helpers'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn() }))
vi.mock('../src/api', () => ({ api }))

import RevisionView from '../src/views/RevisionView.vue'

const stubs = { RouterLink: RouterLinkStub }
const PROBLEMS = [{ id: 27, key: 'LEETCODE:number-of-islands', title: 'Number of Islands', difficulty: 'MEDIUM', url: null, skills: [], attempt_count: 1, last_attempt: null }]

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

async function open(items: ReturnType<typeof revisionItem>[]) {
  serve(api, { '/revisions': revisionList(items), '/skills': SKILLS, '/problems': PROBLEMS })
  api.post.mockResolvedValue({ data: {}, meta: {} })
  const wrapper = mount(RevisionView, { global: { stubs } })
  await vi.waitFor(() => expect(wrapper.find('[data-testid="backlog"]').exists()).toBe(true))
  await flushPromises()
  return wrapper
}

describe('RevisionView', () => {
  it('asks what to recover today and opens on the first tab that has something', async () => {
    const wrapper = await open([revisionItem('CS:db.indexing', 'overdue'), revisionItem('PATTERN:graph.traversal', 'due', { days_overdue: 0, due_date: '2026-10-05' })])
    expect(wrapper.find('h1').text()).toBe('What do you need to recover today?')
    expect(wrapper.find('[data-testid="bucket-overdue"]').attributes('aria-selected')).toBe('true')
    expect(wrapper.findAll('[role="tab"]').map((t) => t.text().replace(/\s+/g, ' '))).toEqual([
      'Due 1', 'Overdue 1', 'Upcoming 0', 'Completed 0', 'Paused 0',
    ])
    expect(wrapper.find('[data-testid="backlog"]').text()).toContain('About 45 min of reviews waiting. A comfortable day is up to 36 min.')
  })

  it('shows reviews as cards in plain words: what, when, how long and a Review action', async () => {
    const wrapper = await open([revisionItem('CS:db.indexing', 'overdue', { lapses: 1 })])
    const card = wrapper.find('[data-testid="item-CS:db.indexing"]')
    expect(card.text()).toContain('Recall: Graphs: BFS and DFS')
    expect(card.text()).toContain('20 min')
    expect(card.text()).toContain('Overdue by 3 days')
    expect(card.text()).toContain('Slipped 1 time')
    expect(card.text()).toContain('Last reviewed 28 Sep')
    expect(card.find('[data-testid="review-CS:db.indexing"]').text()).toBe('Review')
    expect(card.text()).not.toMatch(/CS:db|PATTERN|CONCEPT_EXPLAIN/)
  })

  it('links problem reviews to the problem and opens a closed-book form for the others', async () => {
    const wrapper = await open([
      revisionItem('PROBLEM:27', 'due', { subject_ref: '27', review_kind: 'ATTEMPT', days_overdue: 0 }),
      revisionItem('CS:db.indexing', 'due', { days_overdue: 0 }),
    ])
    await wrapper.find('[data-testid="bucket-due"]').trigger('click')
    const link = wrapper.findAllComponents(RouterLinkStub).find((c) => c.attributes('data-testid') === 'review-PROBLEM:27')
    expect(link?.props('to')).toEqual({ name: 'problem', params: { problemKey: '27' }, query: { revision: 'PROBLEM:27' } })
    expect(wrapper.find('[data-testid="item-PROBLEM:27"]').text()).toContain('Re-solve: Number of Islands')
    await wrapper.find('[data-testid="review-CS:db.indexing"]').trigger('click')
    expect(wrapper.find('[data-testid="assessment-form"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Closed-book')
  })

  it('pauses and resumes through the server', async () => {
    const wrapper = await open([revisionItem('CS:db.indexing', 'overdue'), revisionItem('CS:os.processes', 'suspended', { state: 'SUSPENDED', suspend_reason: 'MANUAL' })])
    await wrapper.find('[data-testid="suspend-CS:db.indexing"]').trigger('click')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/revisions/CS%3Adb.indexing/suspend', {})
    await wrapper.find('[data-testid="bucket-paused"]').trigger('click')
    expect(wrapper.find('[data-testid="item-CS:os.processes"]').text()).toContain('Paused · manual')
    await wrapper.find('[data-testid="resume-CS:os.processes"]').trigger('click')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/revisions/CS%3Aos.processes/resume', {})
  })

  it('shows a friendly empty state per tab', async () => {
    const wrapper = await open([revisionItem('CS:db.indexing', 'overdue')])
    await wrapper.find('[data-testid="bucket-completed"]').trigger('click')
    expect(wrapper.find('[data-testid="empty-state"]').text()).toContain('Nothing graduated yet.')
    await wrapper.find('[data-testid="bucket-due"]').trigger('click')
    expect(wrapper.find('[data-testid="empty-state"]').text()).toContain("You're clear for today.")
    expect(wrapper.find('table').exists()).toBe(false)
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
    const wrapper = mount(AttemptForm, { global: { stubs }, props: { problemId: 27, client, revisionItemKey: 'PROBLEM:27' } })
    await wrapper.find('[data-testid="log-direct"]').trigger('click')
    await wrapper.find('[data-testid="outcome-PASS"]').setValue(true)
    await wrapper.find('[data-testid="minutes"]').setValue('20')
    await wrapper.find('[data-testid="log-form"]').trigger('submit')
    await flushPromises()
    expect(post.mock.calls[0]![1]).toMatchObject({ problem_id: 27, revision_item_key: 'PROBLEM:27', mode: 'REVISION' })
  })
})
