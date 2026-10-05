import { mount, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { ApiError, type ApiClient } from '../src/api/client'
import AttemptForm from '../src/components/practice/AttemptForm.vue'

beforeEach(() => setActivePinia(createPinia()))

function client(post: ApiClient['post']): ApiClient {
  return { get: vi.fn() as ApiClient['get'], post }
}

describe('AttemptForm', () => {
  it('runs start → timer → log and posts the raw observation', async () => {
    let now = 1_000_000
    const post = vi.fn().mockResolvedValue({ data: { id: 7 }, meta: {} })
    const wrapper = mount(AttemptForm, { global: { stubs: { RouterLink: RouterLinkStub } }, props: { problemId: 1, client: client(post), now: () => now } })

    await wrapper.find('[data-testid="confidence-before-4"]').trigger('click')
    await wrapper.find('[data-testid="start"]').trigger('click')
    now += 18 * 60 * 1000 + 20_000 // 18 min 20 s later
    await wrapper.find('[data-testid="finish"]').trigger('click')

    expect((wrapper.find('[data-testid="minutes"]').element as HTMLInputElement).value).toBe('18')
    await wrapper.find('[data-testid="outcome-PASS"]').setValue(true)
    await wrapper.find('[data-testid="explanation"]').setValue('8')
    await wrapper.find('[data-testid="complexity"]').setValue('true')
    await wrapper.find('[data-testid="log-form"]').trigger('submit')
    await nextTick()

    expect(post).toHaveBeenCalledOnce()
    const [path, body] = post.mock.calls[0]!
    expect(path).toBe('/problem-attempts')
    expect(body).toMatchObject({
      problem_id: 1, outcome: 'PASS', time_seconds: 1080, hints_used: 0, self_rating_before: 4,
      explanation_score: 8, complexity_correct: true,
    })
    await vi.waitFor(() => expect(wrapper.find('[data-testid="recorded"]').text()).toBe('Attempt recorded.'))
    expect(wrapper.emitted('recorded')?.[0]?.[0]).toEqual({ id: 7 })
  })

  it('logs a failed attempt with a mistake chip and shows server validation errors', async () => {
    const post = vi.fn().mockRejectedValue(
      new ApiError('VALIDATION_ERROR', 'Request validation failed.', 422, {
        errors: [{ loc: ['body', 'attempted_at'], msg: 'cannot be in the future' }],
      }),
    )
    const wrapper = mount(AttemptForm, { global: { stubs: { RouterLink: RouterLinkStub } }, props: { problemId: 27, client: client(post) } })
    await wrapper.find('[data-testid="log-direct"]').trigger('click')
    await wrapper.find('[data-testid="outcome-FAIL"]').setValue(true)
    await wrapper.find('[data-testid="minutes"]').setValue('31')
    await wrapper.find('[data-testid="hints"]').setValue('2')
    await wrapper.find('[data-testid="mistake-WRONG_PATTERN"]').trigger('click')
    await wrapper.find('[data-testid="log-form"]').trigger('submit')
    await vi.waitFor(() => expect(wrapper.find('[data-testid="form-errors"]').exists()).toBe(true))

    expect(post.mock.calls[0]![1]).toMatchObject({ outcome: 'FAIL', time_seconds: 1860, hints_used: 2, mistakes: ['WRONG_PATTERN'] })
    expect(wrapper.find('[data-testid="form-errors"]').text()).toContain('attempted_at: cannot be in the future')
  })

  it('blocks submission without a result and never calls the server', async () => {
    const post = vi.fn()
    const wrapper = mount(AttemptForm, { global: { stubs: { RouterLink: RouterLinkStub } }, props: { problemId: 1, client: client(post) } })
    await wrapper.find('[data-testid="log-direct"]').trigger('click')
    await wrapper.find('[data-testid="log-form"]').trigger('submit')
    expect(post).not.toHaveBeenCalled()
    expect(wrapper.find('[data-testid="form-errors"]').text()).toContain('Choose a result.')
  })
})
