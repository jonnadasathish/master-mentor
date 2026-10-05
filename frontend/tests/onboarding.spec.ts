import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory } from 'vue-router'
import { ApiError } from '../src/api/client'
import {
  buildOnboardingBody, claimsOf, draftFromProfile, emptyClaims, emptyDraft, MAX_TECHNOLOGIES, stepErrors, toggleClaim,
  toggleTechnology,
} from '../src/practice/onboarding'
import { createAppRouter } from '../src/router'
import { baselineIn, calibrationToday, FIRST_RUN_PROFILE, HISTORY, PROFILE, READINESS, SKILLS, TREE, WEEK } from './fixtures'
import { serve } from './helpers'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn() }))
vi.mock('../src/api', () => ({ api }))

import App from '../src/App.vue'

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  localStorage.clear()
})

describe('onboarding helpers', () => {
  it('prefills from the server and treats the default name "Owner" as unset', () => {
    expect(draftFromProfile(FIRST_RUN_PROFILE).name).toBe('')
    const d = draftFromProfile(PROFILE)
    expect(d).toMatchObject({ name: 'Satish', years: 6, currentRole: 'Backend Engineer', targetDate: '2027-06-28', technologies: ['Python', 'MySQL'] })
    expect(d.budgets).toEqual([90, 90, 90, 90, 90, 75, 75])
    expect(d.claims.strengths).toEqual(['db.core'])
  })

  it('keeps contradictory claims apart, mirroring the server rules', () => {
    let c = toggleClaim(emptyClaims(), 'strengths', 'g')
    c = toggleClaim(c, 'weaknesses', 'g') // weak replaces strong
    expect(claimsOf(c, 'g')).toEqual(['weaknesses'])
    c = toggleClaim(c, 'never_studied', 'g')
    c = toggleClaim(c, 'recently_studied', 'g') // recent replaces never
    expect(claimsOf(c, 'g').sort()).toEqual(['recently_studied', 'weaknesses'])
    c = toggleClaim(c, 'recently_studied', 'g') // toggling again removes it
    expect(claimsOf(c, 'g')).toEqual(['weaknesses'])
    expect(claimsOf(toggleClaim(toggleClaim(emptyClaims(), 'strengths', 'g'), 'recently_studied', 'g'), 'g').sort()).toEqual(['recently_studied', 'strengths'])
  })

  it('toggles technologies case-insensitively and caps the list', () => {
    expect(toggleTechnology(['Python'], 'python')).toEqual([])
    expect(toggleTechnology(['Python'], '  Kafka ')).toEqual(['Python', 'Kafka'])
    expect(toggleTechnology(['Python'], '   ')).toEqual(['Python'])
    const full = Array.from({ length: MAX_TECHNOLOGIES }, (_, i) => `t${i}`)
    expect(toggleTechnology(full, 'one more')).toEqual(full)
  })

  it('checks the steps for fast feedback', () => {
    const d = emptyDraft()
    expect(stepErrors('profile', d)).toEqual(['Tell us what to call you.'])
    d.name = 'Satish'
    d.years = 70
    expect(stepErrors('profile', d)).toEqual(['Years of experience: 0 to 60.'])
    d.years = 6
    expect(stepErrors('profile', d)).toEqual([])
    d.budgets = [0, 0, 0, 0, 0, 0, 0]
    expect(stepErrors('target', d)).toEqual(['Give at least one day some time.'])
    d.budgets = [700, 0, 0, 0, 0, 0, 0]
    expect(stepErrors('target', d)).toEqual(['Daily minutes: 0 to 600 each.'])
  })

  it('builds the API body: self-report separate, goal explicit, blanks as null', () => {
    const d = draftFromProfile(FIRST_RUN_PROFILE)
    Object.assign(d, { name: ' Satish ', years: 6, currentRole: 'Backend Engineer', targetDate: '2027-06-28', technologies: ['Python'] })
    d.claims = toggleClaim(emptyClaims(), 'weaknesses', 'graph.core')
    expect(buildOnboardingBody(d)).toEqual({
      display_name: 'Satish',
      experience: { years: 6, current_role: 'Backend Engineer', previous_role: null },
      technologies: ['Python'], company_profile: '',
      self_report: { strengths: [], weaknesses: ['graph.core'], never_studied: [], recently_studied: [] },
      goal: { target_date: '2027-06-28', weekday_budgets: [90, 90, 90, 90, 90, 75, 75], profile_key: 'backend_fullstack_sde2' },
    })
  })
})

describe('first-run onboarding journey', () => {
  async function open(profile = FIRST_RUN_PROFILE, path = '/') {
    serve(api, {
      '/profile': profile, '/catalog/tree': TREE, '/baseline': baselineIn('NOT_STARTED'), '/today': calibrationToday(0), '/today/week': WEEK,
      '/skills': SKILLS, '/readiness': READINESS, '/readiness/history': HISTORY, '/settings': { timezone: 'Asia/Kolkata', display_name: 'Owner' },
    })
    const router = createAppRouter(createMemoryHistory())
    await router.push(path)
    const wrapper = mount(App, { global: { plugins: [router] }, attachTo: document.body })
    await vi.waitFor(() => expect(wrapper.find('[data-testid="ob-title"]').exists()).toBe(true))
    await flushPromises()
    return { wrapper, router }
  }
  const title = (w: Awaited<ReturnType<typeof open>>['wrapper']) => w.find('[data-testid="ob-title"]').text()
  const click = async (w: Awaited<ReturnType<typeof open>>['wrapper'], id: string) => {
    await w.find(`[data-testid="${id}"]`).trigger('click')
    await flushPromises()
  }

  it('a brand-new user opening the app lands on a focused welcome, without the app navigation', async () => {
    const { wrapper, router } = await open()
    expect(router.currentRoute.value.name).toBe('onboarding')
    expect(title(wrapper)).toBe("Let's build your starting point.")
    expect(wrapper.text()).toContain('Master Mentor first learns what you already know.')
    expect(wrapper.text()).toContain("It will not force you through topics you've already demonstrated.")
    expect(wrapper.find('nav[aria-label="Main"]').exists()).toBe(false)
    expect(wrapper.find('nav[aria-label="Starting profile steps"]').exists()).toBe(true)
    wrapper.unmount()
  })

  it('walks through profile, target, stack and context, explains calibration and saves everything once', async () => {
    api.post.mockResolvedValue({ data: {}, meta: {}, effects: { run_id: 1, skill_deltas: [] } })
    const { wrapper } = await open()
    await click(wrapper, 'ob-next') // welcome -> profile
    expect(title(wrapper)).toBe('A little about you')

    await click(wrapper, 'ob-next') // the name is required
    expect(wrapper.find('[data-testid="ob-errors"]').text()).toContain('Tell us what to call you.')
    await wrapper.find('[data-testid="ob-name"]').setValue('Satish')
    await wrapper.find('[data-testid="ob-years"]').setValue('6')
    await wrapper.find('[data-testid="ob-current-role"]').setValue('Backend Engineer')
    await click(wrapper, 'ob-next')

    expect(title(wrapper)).toBe('Your target')
    expect(wrapper.find('[data-testid="ob-role"]').text()).toContain('SDE-2 benchmark')
    expect(wrapper.find('[data-testid="ob-role"]').text()).toContain('not a claim about any particular company')
    expect(wrapper.text()).toContain('10h a week')
    await wrapper.find('[data-testid="ob-target-date"]').setValue('2027-06-28')
    await click(wrapper, 'ob-next')

    expect(title(wrapper)).toBe('Your current stack')
    expect(wrapper.text()).toContain("using a technology doesn't earn any skill score")
    await click(wrapper, 'ob-tech-Python')
    await click(wrapper, 'ob-tech-Redis')
    await wrapper.find('[data-testid="ob-tech-other"]').setValue('Kafka')
    await click(wrapper, 'ob-tech-add')
    expect(wrapper.find('[data-testid="ob-tech-Kafka"]').attributes('aria-pressed')).toBe('true')
    await click(wrapper, 'ob-next')

    expect(title(wrapper)).toBe('How do you see your skills?')
    expect(wrapper.find('[data-testid="ob-self-report-notice"]').text()).toContain('Self-reported context — not yet verified.')
    expect(wrapper.find('[data-testid="ob-self-report-notice"]').text()).toContain("don't count as proof of skill")
    await click(wrapper, 'ob-claim-strengths-db.core')
    await click(wrapper, 'ob-claim-weaknesses-db.core') // weak replaces strong
    expect(wrapper.find('[data-testid="ob-claim-strengths-db.core"]').attributes('aria-pressed')).toBe('false')
    expect(wrapper.find('[data-testid="ob-claim-weaknesses-db.core"]').attributes('aria-pressed')).toBe('true')
    await click(wrapper, 'ob-next')

    expect(title(wrapper)).toBe('How calibration works')
    const facts = wrapper.find('[data-testid="ob-calibration-facts"]').text()
    expect(facts).toContain('12')
    expect(facts).toContain('~7h')
    expect(facts).toContain('not in one sitting')
    for (const phrase of ['Why it exists', 'What we capture', 'No pass or fail', 'Honest failures are useful']) expect(wrapper.text()).toContain(phrase)
    expect(api.post).not.toHaveBeenCalled() // nothing is saved before the last step

    await click(wrapper, 'ob-next') // Save my starting point
    expect(api.post).toHaveBeenCalledTimes(1)
    const [path, body] = api.post.mock.calls[0]!
    expect(path).toBe('/onboarding/complete')
    expect(body).toMatchObject({
      display_name: 'Satish', experience: { years: 6, current_role: 'Backend Engineer', previous_role: null },
      technologies: ['Python', 'Redis', 'Kafka'], self_report: { weaknesses: ['db.core'], strengths: [] },
      goal: { target_date: '2027-06-28', weekday_budgets: [90, 90, 90, 90, 90, 75, 75] },
    })
    wrapper.unmount()
  })

  it('then shows "Your starting point is ready" with the target, timeline and the calibration entry point', async () => {
    api.post.mockResolvedValue({ data: {}, meta: {}, effects: { run_id: 1, skill_deltas: [] } })
    const { wrapper } = await open()
    // the server's answer after saving: a completed profile with a target
    api.get.mockImplementation((p: string) =>
      Promise.resolve({ data: p === '/profile' ? PROFILE : p === '/baseline' ? { ...baselineIn('NOT_STARTED'), estimated_days: 5 } : [], meta: {} }),
    )
    await wrapper.find('[data-testid="ob-name"]').exists()
    await click(wrapper, 'ob-next')
    await wrapper.find('[data-testid="ob-name"]').setValue('Satish')
    for (let i = 0; i < 5; i++) await click(wrapper, 'ob-next') // profile, target, stack, context, calibration -> save
    await vi.waitFor(() => expect(wrapper.find('[data-testid="ob-ready"]').exists()).toBe(true))
    expect(title(wrapper)).toBe('Your starting point is ready.')
    const ready = wrapper.find('[data-testid="ob-ready"]').text()
    expect(ready).toContain('SDE-2 benchmark')
    expect(ready).toMatch(/38\.1 weeks\s*·\s*June 2027/)
    expect(ready).toContain('10h a week')
    expect(ready).toContain('Calibrate your skills')
    expect(ready).toContain('12 baseline assessments')
    expect(ready).toContain('spread across your normal schedule')
    expect(ready).toContain('roughly 5 days')
    expect(wrapper.find('[data-testid="ob-start-calibration"]').text()).toContain('Start calibration')
    wrapper.unmount()
  })

  it('shows what the server rejected in plain words and keeps the user on the step', async () => {
    api.post.mockRejectedValue(new ApiError('VALIDATION_ERROR', 'Request validation failed.', 422, { errors: [{ loc: ['body', 'goal', 'target_date'], msg: 'must be in the future' }] }))
    const { wrapper } = await open()
    await click(wrapper, 'ob-next')
    await wrapper.find('[data-testid="ob-name"]').setValue('Satish')
    for (let i = 0; i < 5; i++) await click(wrapper, 'ob-next')
    expect(wrapper.find('[data-testid="ob-errors"]').text()).toContain('target date: must be in the future')
    expect(title(wrapper)).toBe('How calibration works')
    wrapper.unmount()
  })

  it('opened again later it edits the profile: prefilled, no welcome, saved in place', async () => {
    api.post.mockResolvedValue({ data: {}, meta: {}, effects: { run_id: 1, skill_deltas: [] } })
    const { wrapper, router } = await open(PROFILE, '/onboarding')
    expect(title(wrapper)).toBe('Edit your starting profile')
    expect((wrapper.find('[data-testid="ob-name"]').element as HTMLInputElement).value).toBe('Satish')
    expect((wrapper.find('[data-testid="ob-years"]').element as HTMLInputElement).value).toBe('6')
    for (let i = 0; i < 3; i++) await click(wrapper, 'ob-next')
    expect(wrapper.find('[data-testid="ob-next"]').text()).toBe('Save changes')
    await click(wrapper, 'ob-next')
    expect(api.post.mock.calls[0]![0]).toBe('/onboarding/complete')
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('progress'))
    wrapper.unmount()
  })

  it('has labelled fields and a focusable heading for keyboard and screen-reader users', async () => {
    const { wrapper } = await open()
    await click(wrapper, 'ob-next')
    expect(wrapper.find('h1').attributes('tabindex')).toBe('-1')
    for (const input of wrapper.findAll('input')) expect(input.element.closest('label'), input.attributes('data-testid')).not.toBeNull()
    expect(wrapper.find('[data-testid="ob-name"]').element.closest('label')?.textContent).toContain('What should we call you?')
    wrapper.unmount()
  })
})
