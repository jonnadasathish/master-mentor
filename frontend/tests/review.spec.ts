import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { review, SKILLS } from './fixtures'
import { serve } from './helpers'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn() }))
vi.mock('../src/api', () => ({ api }))

import WeeklyReviewView from '../src/views/WeeklyReviewView.vue'

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

async function open(r = review()) {
  serve(api, { '/weekly-reviews/latest': r, '/weekly-reviews': [r], '/skills': SKILLS })
  api.post.mockResolvedValue({ data: { ...r, reflection: { next_priority: 'x' } }, meta: {} })
  const wrapper = mount(WeeklyReviewView, { global: { stubs: { RouterLink: RouterLinkStub } } })
  await vi.waitFor(() => expect(wrapper.find('[data-testid="reflection-form"]').exists() || wrapper.find('[data-testid="empty-state"]').exists()).toBe(true))
  await flushPromises()
  return wrapper
}

describe('WeeklyReviewView', () => {
  it('reads like a mentor conversation: improved, regressed, biggest gap, revision, recommendation', async () => {
    const wrapper = await open()
    expect(wrapper.find('h1').text()).toBe('This is what changed this week.')
    const headings = wrapper.findAll('h2').map((h) => h.text())
    expect(headings).toEqual(expect.arrayContaining(['You improved', 'You regressed', 'Your biggest gap', 'Revision health', 'Mentor recommendation']))
    const improved = wrapper.find('[data-testid="improved"]').text()
    expect(improved).toContain('moved from 44 to 59')
    expect(improved).toContain('Caching strategies is less of a gap than last week.')
    expect(wrapper.find('[data-testid="regressed"]').text()).toContain('slipped from 50 to 41')
    expect(wrapper.find('[data-testid="biggest-gap"]').text()).toContain('Graphs: BFS and DFS')
    expect(wrapper.text()).toContain('You did 83% of the reviews planned this week.')
    expect(wrapper.text()).toContain('Work on Graphs: BFS and DFS, Caching strategies.')
    expect(wrapper.text()).toContain('Readiness moved from Foundation to Developing.')
  })

  it("saves the reflection with the mentor's suggested focus when you accept next week's focus", async () => {
    const wrapper = await open()
    expect((wrapper.find('[data-testid="reflection-next_priority"]').element as HTMLTextAreaElement).value).toBe('Work on Graphs: BFS and DFS, Caching strategies.')
    await wrapper.find('[data-testid="reflection-improved"]').setValue('graphs')
    await wrapper.find('[data-testid="reflection-form"]').trigger('submit')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/weekly-reviews/2026-09-28/reflection', expect.objectContaining({ improved: 'graphs', next_priority: 'Work on Graphs: BFS and DFS, Caching strategies.' }))
    expect(wrapper.find('[role="status"]').text()).toContain("Next week's focus is on record.")
    expect(wrapper.find('[data-testid="accept"]').text()).toBe("Accept next week's focus")
  })

  it('treats a week with nothing planned or practised as a quiet week', async () => {
    const wrapper = await open(review({ active_days: 0, planned_minutes: 0, completed_minutes: 0 }))
    expect(wrapper.find('[data-testid="empty-state"]').text()).toContain('A quiet week.')
    expect(wrapper.find('[data-testid="reflection-form"]').exists()).toBe(false)
  })

  it('says so when nothing improved or regressed', async () => {
    const wrapper = await open(review({ strongest_improvement: null, biggest_regression: null, gap_changes: [] }))
    expect(wrapper.text()).toContain('No skill moved up enough to call out this week.')
    expect(wrapper.text()).toContain('Nothing slipped.')
  })
})
