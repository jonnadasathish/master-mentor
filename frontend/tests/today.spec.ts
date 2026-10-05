import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { HttpClient } from '../src/api/client'
import type { PlanItem } from '../src/api/types'
import MissionCard from '../src/components/missions/MissionCard.vue'
import { missionText } from '../src/presentation/mission'
import { baseline, baselineIn, baselineItem, calibrationToday, HISTORY, planItem, PROFILE, READINESS, SKILLS, today, WEEK } from './fixtures'
import { networkDown, serve } from './helpers'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn() }))
vi.mock('../src/api', () => ({ api }))

import TodayView from '../src/views/TodayView.vue'

const stubs = { RouterLink: RouterLinkStub }
const SETTINGS = { timezone: 'Asia/Kolkata', display_name: 'Satish' }

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  localStorage.clear()
})

function routes(todayData: unknown, extra: Record<string, unknown> = {}) {
  serve(api, {
    '/today': todayData, '/today/week': WEEK, '/skills': SKILLS, '/readiness': READINESS, '/readiness/history': HISTORY,
    '/settings': SETTINGS, '/baseline': baselineIn('COMPLETE'), '/profile': PROFILE, ...extra,
  })
}

async function mountToday() {
  const wrapper = mount(TodayView, { global: { stubs } })
  await vi.waitFor(() => expect(wrapper.find('[data-testid="today-header"]').exists()).toBe(true))
  await flushPromises()
  return wrapper
}

describe('Today: calibration', () => {
  it('before any evidence: starts with a clear "Start calibration", the timeline and what is left', async () => {
    routes(calibrationToday(0, [baselineItem({ battery_item_key: 'M0-B01', minutes: 15 })]), { '/baseline': baselineIn('NOT_STARTED') })
    const wrapper = await mountToday()
    const cta = wrapper.find('[data-testid="calibration-cta"]')
    expect(cta.attributes('data-phase')).toBe('NOT_STARTED')
    expect(cta.text()).toContain("Let's measure where you are.")
    const button = wrapper.findAllComponents(RouterLinkStub).find((c) => c.attributes('data-testid') === 'continue-calibration')
    expect(button?.text()).toContain('Start calibration')
    expect(button?.props('to')).toEqual({ name: 'calibrate', query: { start: '1' } })
    const progress = wrapper.find('[data-testid="calibration-progress"]')
    expect(progress.text()).toContain('0 / 12')
    expect(progress.text()).toContain('0 / 123')
    expect(wrapper.find('[data-testid="calibration-effort"]').text()).toContain('About 7h of assessments left, roughly 5 days at your usual daily time')
    expect(wrapper.find('[data-testid="calibration-effort"]').text()).toContain('not in one sitting')
    expect(wrapper.find('[data-testid="calibration-timeline"]').text()).toMatch(/Interview target\s*June 2027/)
    expect(wrapper.find('[data-testid="calibration-timeline"]').text()).toMatch(/Time remaining\s*38 weeks/)
    expect(wrapper.find('[data-testid="what-calibration-means"]').text()).toContain('There is no pass or fail')
  })

  it('shows friendly diagnostic names, never the internal ids', async () => {
    routes(calibrationToday(0, [baselineItem({ battery_item_key: 'M0-B01', minutes: 15 })]), { '/baseline': baselineIn('NOT_STARTED') })
    const wrapper = await mountToday()
    const list = wrapper.find('[data-testid="diagnostic-list"]')
    expect(list.text()).toContain('Familiarity sweep')
    expect(list.text()).toContain('15 min')
    expect(list.text()).toContain('To do')
    expect(wrapper.text()).not.toMatch(/M0-B\d\d/)
    expect(wrapper.find('[data-testid="start-1"]').exists()).toBe(false) // the full cards live on the calibration page
  })

  it('while in progress it says how many skills are measured and offers "Continue calibration"', async () => {
    routes(calibrationToday(2, [baselineItem({ battery_item_key: 'M0-B03' })]), { '/baseline': baselineIn('IN_PROGRESS') })
    const wrapper = await mountToday()
    const cta = wrapper.find('[data-testid="calibration-cta"]')
    expect(cta.text()).toContain("We've measured 8 of 123 required skills.")
    expect(cta.text()).toContain('Your personalized plan will appear once the baseline has enough evidence.')
    expect(cta.text()).toContain('Continue calibration')
    expect(cta.text()).not.toContain('View my roadmap')
    expect(wrapper.find('[data-testid="calibration-progress"]').text()).toContain('2 / 12')
    expect(wrapper.find('[data-testid="calibration-progress"]').text()).toContain('8 / 123')
  })

  it('once enough is measured it offers the roadmap and still lets you continue', async () => {
    routes(calibrationToday(2, [baselineItem({ battery_item_key: 'M0-B03' })]), { '/baseline': baselineIn('ENOUGH_MEASURED') })
    const wrapper = await mountToday()
    const cta = wrapper.find('[data-testid="calibration-cta"]')
    expect(cta.text()).toContain('We have enough evidence to build your initial roadmap.')
    const links = wrapper.findAllComponents(RouterLinkStub)
    expect(links.find((c) => c.attributes('data-testid') === 'view-roadmap')?.props('to')).toEqual({ name: 'roadmap' })
    expect(links.find((c) => c.attributes('data-testid') === 'continue-calibration')?.text()).toContain('Continue calibration')
  })

  it('shows "not measured yet" as a calm state, not an error', async () => {
    routes(calibrationToday(0), { '/baseline': baselineIn('NOT_STARTED') })
    const wrapper = await mountToday()
    const card = wrapper.find('[data-testid="readiness-card"]')
    expect(card.find('[data-testid="readiness-state"]').text()).toBe('Not measured yet')
    expect(card.text()).toContain('Calibrating')
    expect(card.text()).toContain('This is expected')
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  })

  it('leaves the mentor message and mission cards to the personalized mode', async () => {
    routes(calibrationToday(2), { '/baseline': baselineIn('IN_PROGRESS') })
    const wrapper = await mountToday()
    expect(wrapper.find('[data-testid="mentor-message"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="top-gaps"]').exists()).toBe(false)
  })

  it('switches to the personalized mentor once every baseline task is done', async () => {
    routes(today(), { '/baseline': baselineIn('COMPLETE') })
    const wrapper = await mountToday()
    expect(wrapper.find('[data-testid="calibration-cta"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="mentor-message"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="plan-item-1"]').exists()).toBe(true)
  })

  it('says a finished baseline with unmeasured areas is not "calibrating"', async () => {
    routes(
      today({
        readiness: { state: 'NOT_MEASURED', weighted_score: 3, limiting_component: 'dsa', blockers: [
          { gate: 'G0', message: 'DSA assessed 69% < 70%', component: 'dsa', skill: null, actual: 69, required: 70 },
        ] },
      }),
    )
    const wrapper = await mountToday()
    const card = wrapper.find('[data-testid="readiness-card"]')
    expect(card.text()).not.toContain("We're calibrating")
    expect(card.find('[data-testid="readiness-needs"]').text()).toContain('DSA assessed 69% < 70%')
    expect(card.text()).not.toMatch(/\bG0\b/)
  })
})

describe('Today: after the baseline', () => {
  it('shows the skill map banner, readiness, gaps, the mentor message and the missions', async () => {
    routes(today())
    const wrapper = await mountToday()
    const banner = wrapper.find('[data-testid="skill-map-ready"]')
    expect(banner.text()).toContain('Baseline complete. Your personal roadmap is ready.')
    expect(banner.find('[data-testid="banner-roadmap"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="calibration-cta"]').exists()).toBe(false)

    expect(wrapper.find('[data-testid="today-phase"]').text()).toBe('Day 27 · Building foundations · 38 weeks to your interview (June 2027)')

    const readiness = wrapper.find('[data-testid="readiness-card"]')
    expect(readiness.find('[data-testid="readiness-score"]').text()).toContain('74')
    expect(readiness.text()).toContain('Solid progress')
    expect(readiness.text()).toContain('Holding you back most: System Design')
    const names = readiness.findAll('.components li .name').map((n) => n.text())
    expect(names).toEqual(['DSA', 'CS Fundamentals', 'System Design'])
    expect(readiness.find('[data-testid="readiness-trend"]').text()).toContain('Up 4 since 2026-09-28')
    expect(readiness.text()).not.toMatch(/\bG\d\b|NOT_MEASURED|DEVELOPING/)

    const gaps = wrapper.find('[data-testid="top-gaps"]')
    expect(gaps.findAll('li')).toHaveLength(2)
    expect(gaps.find('[data-testid="gap-graph.traversal"]').text()).toContain('Graphs: BFS and DFS')
    expect(gaps.find('[data-testid="gap-graph.traversal"]').text()).toContain('43 / 80')
    expect(gaps.find('[data-testid="gap-graph.traversal"]').text()).toContain('Critical')
    expect(gaps.find('[data-testid="gap-sd.caching"]').text()).toContain('51 / 80')

    const message = wrapper.find('[data-testid="mentor-message"]').text()
    expect(message).toContain('Graphs: BFS and DFS is the highest-value gap.')

    const week = wrapper.find('[data-testid="week-progress"]')
    expect(week.text()).toContain('8h 30m')
    expect(week.text()).toContain('/ 10h')
    expect(week.text()).toContain('DSA & coding')
    expect(week.text()).toContain('revision 83% done')
    expect(wrapper.find('[data-testid="revision-glance"]').text()).toContain('3 reviews waiting')
  })

  it('shows the mission with what, how long, why, expected outcome and a Start action', async () => {
    routes(today())
    const wrapper = await mountToday()
    const card = wrapper.find('[data-testid="plan-item-1"]')
    expect(card.text()).toContain('01')
    expect(card.text()).toContain('Pattern drill: Graphs: BFS and DFS')
    expect(card.text()).toContain('35 min')
    expect(card.text()).toContain('Why this matters')
    expect(card.text()).toContain('Your Graphs: BFS and DFS score is 42, against a target of 80.')
    expect(card.text()).toContain('You\'ve been picking the wrong approach.')
    expect(card.text()).toContain('Expected outcome: A score of 70 or more')
    expect(card.text()).not.toMatch(/outcome_points|L3 evidence|PATTERN_DRILL/)
    expect(card.find('[data-testid="start-1"]').text()).toContain('Start')
    expect(wrapper.find('[data-testid="plan-budget"]').text()).toBe('35 min planned of 1h 30m')
  })

  it('lets the banner be dismissed for good', async () => {
    routes(today())
    const wrapper = await mountToday()
    await wrapper.find('[data-testid="skill-map-ready"] button').trigger('click')
    expect(wrapper.find('[data-testid="skill-map-ready"]').exists()).toBe(false)
    expect(localStorage.getItem('mm.skillMapSeen')).toBe('1')
    const again = await mountToday()
    expect(again.find('[data-testid="skill-map-ready"]').exists()).toBe(false)
  })

  it('keeps finished missions on the page and says the plan is done', async () => {
    const done = [
      planItem({ id: 7, position: 1, status: 'DONE', completed_at: '2026-10-05T08:00:00Z' }),
      planItem({ id: 8, position: 2, status: 'SKIPPED', skip_reason: 'NO_TIME', candidate_key: 'GAP:sd.caching', skill: 'sd.caching', stage: 'GUIDED' }),
    ]
    routes(today({}, done))
    const wrapper = await mountToday()
    expect(wrapper.find('[data-testid="plan-item-1"]').text()).toContain('Completed')
    expect(wrapper.find('[data-testid="plan-item-1"]').text()).toContain('35 min')
    expect(wrapper.find('[data-testid="plan-item-2"]').text()).toContain('Skipped · No time today')
    expect(wrapper.find('[data-testid="day-finished"]').text()).toContain("That's today's plan.")
    expect(wrapper.find('[data-testid="start-1"]').exists()).toBe(false)
  })

  it('collapses a long stop list and swaps skill keys for names', async () => {
    const stop = ['arrays.traversal', 'graph.traversal', 'sd.caching', 'a.b', 'c.d'].map((skill) => ({
      skill, code: 'PARKED_DEADLINE', instruction: `Stop studying ${skill} until after the target date.`, minutes_7d: 0,
    }))
    const data = today()
    data.plan.stop_list = stop
    routes(data)
    const wrapper = await mountToday()
    const list = wrapper.find('[data-testid="stop-list"]')
    expect(list.findAll('li')).toHaveLength(3)
    expect(list.text()).toContain('Stop studying Array traversal until after the target date.')
    expect(list.text()).not.toContain('arrays.traversal')
    await wrapper.find('.more-stops').trigger('click')
    expect(wrapper.find('[data-testid="stop-list"]').findAll('li')).toHaveLength(5)
  })

  it('shows nothing-critical when no gap needs attention', async () => {
    const data = today()
    data.top_gaps = []
    routes(data)
    const wrapper = await mountToday()
    expect(wrapper.text()).toContain('Nothing critical right now.')
  })

  it('marks sections with the order classes the phone layout recomposes by', async () => {
    routes(today())
    const wrapper = await mountToday()
    for (const cls of ['o-mentor', 'o-missions', 'o-readiness', 'o-gaps', 'o-week', 'o-revision']) {
      expect(wrapper.find(`.${cls}`).exists(), cls).toBe(true)
    }
  })
})

describe('Today: loading and errors', () => {
  it('shows a skeleton while the plan is loading', async () => {
    routes(today())
    api.get.mockImplementation(() => new Promise(() => undefined))
    const wrapper = mount(TodayView, { global: { stubs } })
    await flushPromises()
    expect(wrapper.find('[data-testid="today-skeleton"]').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('Loading')
  })

  it("explains a failure in plain words, hides the code until asked, and retries", async () => {
    routes(networkDown())
    const wrapper = mount(TodayView, { global: { stubs } })
    await vi.waitFor(() => expect(wrapper.find('[data-testid="error-state"]').exists()).toBe(true))
    const box = wrapper.find('[data-testid="error-state"]')
    expect(box.text()).toContain("Master Mentor can't reach the preparation engine right now.")
    expect(box.find('details').attributes('open')).toBeUndefined()
    expect(box.find('details').text()).toContain('NETWORK_ERROR')
    expect(box.text().split('Technical details')[0]).not.toMatch(/HTTP|NETWORK_ERROR|503/)

    routes(today())
    await box.find('[data-testid="retry"]').trigger('click')
    await vi.waitFor(() => expect(wrapper.find('[data-testid="today-header"]').exists()).toBe(true))
  })
})

describe('MissionCard', () => {
  function client(): HttpClient {
    return { get: vi.fn(), post: vi.fn().mockResolvedValue({ data: {}, meta: {} }), patch: vi.fn() } as unknown as HttpClient
  }
  const ctx = { nameOf: (k: string) => (k === 'graph.traversal' ? 'Graphs: BFS and DFS' : k), componentOf: () => 'dsa', battery: baseline(0).items }
  const props = (item: PlanItem, extra: Record<string, unknown> = {}) => ({ item, client: client(), text: missionText(item, ctx), ...extra })
  const posts = (c: HttpClient) => (c.post as ReturnType<typeof vi.fn>).mock.calls

  it('posts mark-studied, do-it-tomorrow and a skip with its reason from the other options', async () => {
    const p = props(planItem())
    const wrapper = mount(MissionCard, { global: { stubs }, props: p })
    await wrapper.find('[data-testid="more-1"]').trigger('click')
    await wrapper.find('[data-testid="no-evidence-1"]').trigger('click')
    await wrapper.find('[data-testid="defer-1"]').trigger('click')
    await wrapper.find('[data-testid="skip-1"]').trigger('click')
    await wrapper.find('[data-testid="skip-1-TOO_HARD"]').trigger('click')
    await flushPromises()
    expect(posts(p.client)).toEqual([
      ['/plan/items/7/complete', { no_evidence: true }],
      ['/plan/items/7/defer', {}],
      ['/plan/items/7/skip', { skip_reason: 'TOO_HARD' }],
    ])
    expect(wrapper.emitted('changed')).toHaveLength(3)
  })

  it('logs an attempt through the plan item so the server links it', async () => {
    const p = props(planItem())
    ;(p.client.post as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { item: {}, observation: { id: 3 } }, meta: {}, effects: { run_id: 1, skill_deltas: [] } })
    const wrapper = mount(MissionCard, { global: { stubs }, props: p })
    await wrapper.find('[data-testid="log-1"]').trigger('click')
    await wrapper.find('[data-testid="log-direct"]').trigger('click')
    expect(wrapper.emitted('completed')).toBeUndefined()
    await wrapper.find('[data-testid="outcome-PASS"]').setValue(true)
    await wrapper.find('[data-testid="minutes"]').setValue('30')
    await wrapper.find('[data-testid="log-form"]').trigger('submit')
    await flushPromises()
    const [path, body] = posts(p.client)[0]!
    expect(path).toBe('/plan/items/7/complete')
    expect(body).toMatchObject({ observation: { type: 'ATTEMPT', body: { problem_id: 17, outcome: 'PASS', time_seconds: 1800 } } })
    expect(wrapper.emitted('completed')?.[0]).toEqual([{ run_id: 1, skill_deltas: [] }])
  })

  it('Start runs the timer against the limit and opens the result form with the elapsed minutes', async () => {
    vi.useFakeTimers()
    let now = 1_000_000
    const p = props(planItem({ minutes: 40, template: { key: 'dsa.timed', observation: { kind: 'ATTEMPT' }, pass_rule: 'outcome_points >= 70', output_level: 4, next_on_pass: null } }), { now: () => now })
    const wrapper = mount(MissionCard, { global: { stubs }, props: p })
    await wrapper.find('[data-testid="start-1"]').trigger('click')
    await flushPromises()
    now += 65_000
    vi.advanceTimersByTime(1000)
    await wrapper.vm.$nextTick()
    expect(posts(p.client)[0]).toEqual(['/plan/items/7/start', {}])
    expect(wrapper.find('[data-testid="plan-item-1"]').attributes('data-phase')).toBe('in-progress')
    expect(wrapper.find('[data-testid="timer-1"]').text()).toBe('⏱ 01:05 / 40:00')
    await wrapper.find('[data-testid="log-1"]').trigger('click')
    expect((wrapper.find('[data-testid="minutes"]').element as HTMLInputElement).value).toBe('1')
    vi.useRealTimers()
  })

  it('shows the numbers behind the reason on request', async () => {
    const wrapper = mount(MissionCard, { global: { stubs }, props: props(planItem()) })
    expect(wrapper.find('[data-testid="why-panel-1"]').exists()).toBe(false)
    await wrapper.find('[data-testid="why-1"]').trigger('click')
    expect(wrapper.find('[data-testid="why-panel-1"]').text()).toContain('Current score')
    expect(wrapper.find('[data-testid="why-panel-1"]').text()).toContain('42')
  })

  it('transforms when completed, keeps what changed, and offers no actions', () => {
    const item = planItem({ status: 'DONE' })
    const wrapper = mount(MissionCard, {
      global: { stubs }, props: props(item, { result: { run_id: 1, skill_deltas: [{ skill_key: 'graph.traversal', before: { score: 42, effective: 30, level: 2, confidence: 'LOW' }, after: { score: 51, effective: 43, level: 3, confidence: 'MEDIUM' } }] } }),
    })
    expect(wrapper.attributes('data-phase')).toBe('completed')
    expect(wrapper.text()).toContain('Pattern drill: Graphs: BFS and DFS')
    expect(wrapper.text()).toMatch(/35 min\s*·\s*Completed/)
    expect(wrapper.find('[data-testid="effects-panel"]').text()).toContain('42 → 51')
    expect(wrapper.find('[data-testid="log-1"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="start-1"]').exists()).toBe(false)
  })

  it('shows deferred missions as moved to tomorrow', () => {
    const wrapper = mount(MissionCard, { global: { stubs }, props: props(planItem({ status: 'DEFERRED' })) })
    expect(wrapper.attributes('data-phase')).toBe('deferred')
    expect(wrapper.text()).toContain('Moved to tomorrow')
  })

  it('shows a blocked mission with its reason and no Start', () => {
    const wrapper = mount(MissionCard, { global: { stubs }, props: props(planItem(), { blockedReason: 'Practice Graph representation first.' }) })
    expect(wrapper.attributes('data-phase')).toBe('blocked')
    expect(wrapper.text()).toContain('Practice Graph representation first.')
    expect(wrapper.text()).toContain('Blocked')
    expect(wrapper.find('[data-testid="start-1"]').exists()).toBe(false)
  })

  it('names baseline missions after their assessment and says what you will do', () => {
    const item = baselineItem({ battery_item_key: 'M0-B02', minutes: 60 })
    const text = missionText(item, ctx)
    expect(text.title).toBe('DSA diagnostic A')
    expect(text.task).toBe('2 unseen MEDIUM problems (arrays, hashing, two pointers, sliding window), timed')
    expect(text.why[0]).toContain("where you're starting from")
    expect(missionText(baselineItem({ battery_item_key: 'M0-B04' }), ctx).title).toBe('CS quiz: DBMS')
  })
})
