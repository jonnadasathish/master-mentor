import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { currentState, personalRoadmap, ROADMAP, SKILLS } from './fixtures'
import { serve } from './helpers'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn() }))
vi.mock('../src/api', () => ({ api }))

import SelfReportVsObserved from '../src/components/progress/SelfReportVsObserved.vue'
import PersonalRoadmap from '../src/components/roadmap/PersonalRoadmap.vue'
import { useSkillsStore } from '../src/stores/data'
import RoadmapView from '../src/views/RoadmapView.vue'

const stubs = { RouterLink: RouterLinkStub }

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  useSkillsStore().data = SKILLS
})

describe('Personal roadmap', () => {
  const view = (roadmap = personalRoadmap()) => mount(PersonalRoadmap, { global: { stubs }, props: { roadmap } })

  it('waits for calibration instead of guessing', () => {
    for (const phase of ['NOT_STARTED', 'IN_PROGRESS'] as const) {
      const wrapper = view(personalRoadmap(phase))
      expect(wrapper.find('[data-testid="empty-state"]').text()).toContain('Your personal roadmap appears after calibration.')
      expect(wrapper.find('[data-testid="focus-now"]').exists()).toBe(false)
      expect(wrapper.find('[data-testid="roadmap-to-calibrate"]').text()).toContain(phase === 'NOT_STARTED' ? 'Start calibration' : 'Continue calibration')
    }
    expect(view(personalRoadmap('COMPLETE', { available: false })).find('[data-testid="focus-now"]').exists()).toBe(false)
  })

  it('shows the phase and timeline, then what to focus on, from the engine\'s own list', () => {
    const wrapper = view()
    const phase = wrapper.find('[data-testid="roadmap-phase"]').text()
    expect(phase).toContain('Building foundations')
    expect(phase).toMatch(/Interview target\s*June 2027/)
    expect(phase).toMatch(/Time remaining\s*38\.1 weeks/)
    const focus = wrapper.find('[data-testid="focus-now"]')
    expect(focus.findAll('[data-testid^="roadmap-item-"]').map((i) => i.find('a').text())).toEqual(['Graphs: BFS and DFS', 'Caching strategies'])
  })

  it('each focus item shows score, target, kind of work, reason, effort and what it waits on', () => {
    const wrapper = view()
    const graphs = wrapper.find('[data-testid="roadmap-item-graph.traversal"]').text()
    expect(graphs).toContain('Consolidate')
    expect(graphs).toContain('43 / 80')
    expect(graphs).toContain('Pattern recognition.')
    expect(graphs).toContain('Recent attempts keep failing.')
    expect(graphs).toContain('Next: Pattern drill · 25 min')
    expect(graphs).toContain('Prerequisites ready')
    const caching = wrapper.find('[data-testid="roadmap-item-sd.caching"]').text()
    expect(caching).toContain('Build')
    expect(caching).toContain('20 / 80')
    expect(caching).toContain('Next: Learn · 40 min')
    expect(wrapper.find('[data-testid="roadmap-item-sd.caching"] [data-testid="waiting-on"]').text()).toContain('Needs System design basics first (30 of 50)')
  })

  it('shows strong skills as already strong (not re-taught), later items, parked and unmeasured counts', () => {
    const wrapper = view()
    expect(wrapper.find('[data-testid="strong-skills"]').text()).toContain('Array traversal')
    expect(wrapper.text()).toContain("They won't be taught again.")
    expect(wrapper.find('[data-testid="later"]').text()).toContain('Dynamic programming')
    expect(wrapper.find('[data-testid="focus-now"]').text()).not.toContain('Array traversal')
    expect(wrapper.find('[data-testid="unmeasured"]').text()).toMatch(/25\s*skills have no evidence yet/)
    expect(wrapper.text()).toContain('Parked')
  })

  it('"Why is this my roadmap?" lists what it is based on, with server numbers and no jargon', async () => {
    const wrapper = view()
    expect(wrapper.find('[data-testid="why-roadmap-body"]').exists()).toBe(false)
    await wrapper.find('[data-testid="why-roadmap"]').trigger('click')
    const body = wrapper.find('[data-testid="why-roadmap-body"]').text()
    expect(body).toContain('Your target role: Software Engineer — Backend/Full-Stack (SDE-2 benchmark)')
    expect(body).toContain('Your target date: June 2027')
    expect(body).toContain('98 of 123 required skills')
    expect(body).toContain('Your biggest gaps: Graphs: BFS and DFS; Caching strategies')
    expect(body).toContain('4 skills wait for a weaker prerequisite')
    expect(body).toContain('1 review overdue')
    const why = wrapper.find('[data-testid="why-graph.traversal"]').text()
    expect(why).toContain('Graphs: BFS and DFS is prioritized because your current score is 43 against a target of 80.')
    expect(why).toContain('3 of your last 5 attempts failed.')
    expect(why).toContain('You missed the pattern in 3 of your last 4 attempts.')
    expect(body).not.toMatch(/\bG\d\b|ruleset|gap state|mentor run|L\d evidence/i)
  })

  it('says "Your plan changed" only when the engine reports a change, and explains it from its reasons', () => {
    expect(view().find('[data-testid="roadmap-changed"]').exists()).toBe(false)
    const changed = personalRoadmap('COMPLETE', {
      changes: {
        since: '2026-10-04', changed: true,
        entered: [{ skill_key: 'sd.caching', name: 'Caching strategies', priority_before: 20, priority_after: 60, reason_codes: ['MOCK_WEAKNESS'] }],
        left: [{ skill_key: 'dp.core', name: 'Dynamic programming', priority_before: 50, priority_after: 30, reason_codes: [] }],
      },
    })
    const text = view(changed).find('[data-testid="roadmap-changed"]').text()
    expect(text).toContain('Your plan changed')
    expect(text).toContain('Caching strategies moved into your focus: it showed up as a weakness in a mock')
    expect(text).toContain('Dynamic programming moved out of your focus.')
  })

  it('marks an initial roadmap while calibration is still open', () => {
    expect(view(personalRoadmap('ENOUGH_MEASURED')).find('[data-testid="roadmap-initial"]').text()).toContain('This is your initial roadmap.')
    expect(view(personalRoadmap('COMPLETE')).find('[data-testid="roadmap-initial"]').exists()).toBe(false)
  })

  it('the Roadmap page opens on your roadmap, with the planned order one tab away', async () => {
    serve(api, { '/roadmap/personal': personalRoadmap(), '/roadmap': ROADMAP, '/skills': SKILLS })
    const wrapper = mount(RoadmapView, { global: { stubs } })
    await vi.waitFor(() => expect(wrapper.find('[data-testid="personal-roadmap"]').exists()).toBe(true))
    await flushPromises()
    expect(wrapper.find('h1').text()).toBe('Your personal roadmap')
    expect(wrapper.find('[data-testid="view-personal"]').attributes('aria-selected')).toBe('true')
    expect(wrapper.find('[data-testid="roadmap"]').exists()).toBe(false)
    await wrapper.find('[data-testid="view-planned"]').trigger('click')
    await vi.waitFor(() => expect(wrapper.find('[data-testid="roadmap"]').exists()).toBe(true))
  })
})

describe('Self-reported vs observed', () => {
  const groups = currentState().self_reported
  const view = () => mount(SelfReportVsObserved, { global: { stubs }, props: { groups } })

  it('keeps what you said visibly apart from what was measured', () => {
    const wrapper = view()
    const databases = wrapper.find('[data-testid="compare-db.core"]')
    const said = databases.find('[data-testid="self-reported"]')
    const measured = databases.find('[data-testid="observed"]')
    expect(said.text()).toContain('You said')
    expect(said.text()).toContain('Strong')
    expect(said.text()).toContain('Self-reported · not verified')
    expect(measured.text()).toContain('Measured')
    expect(measured.text()).toContain('1 of 2 skills measured')
    expect(measured.text()).toContain('Indexing')
    expect(measured.text()).toContain('82 / 80')
    expect(measured.text()).toContain('high confidence')
    expect(said.classes()).not.toEqual(measured.classes())
  })

  it('shows "new to me" as a self-rating, not as a measured result', () => {
    const declared = [{ ...groups[0]!, measured: 0, skills: [{ skill_key: 'db.indexing', name: 'Indexing', score: 0, target: 80, confidence: 'LOW', status: 'CRITICAL', declared_unknown: true }] }]
    const wrapper = mount(SelfReportVsObserved, { global: { stubs }, props: { groups: declared } })
    const observed = wrapper.find('[data-testid="observed"]').text()
    expect(observed).toContain('0 of 2 skills measured by tasks')
    expect(wrapper.find('[data-testid="declared-unknown"]').text()).toContain('You marked this as new to you')
    expect(observed).not.toContain('0 / 80')
  })

  it('shows a focus skill the user only rated as unknown with a self-rating note', () => {
    const roadmap = personalRoadmap()
    roadmap.focus_now = [{ ...roadmap.focus_now[0]!, declared_unknown: true, score: 0 }, ...roadmap.focus_now.slice(1)]
    const wrapper = mount(PersonalRoadmap, { global: { stubs }, props: { roadmap } })
    expect(wrapper.find('[data-testid="roadmap-item-graph.traversal"] [data-testid="declared-unknown"]').text()).toContain('self-rating, not a task result')
    expect(wrapper.find('[data-testid="roadmap-item-sd.caching"] [data-testid="declared-unknown"]').exists()).toBe(false)
  })

  it('shows a claim with no evidence as not measured, and several claims for one topic', () => {
    const graphs = view().find('[data-testid="compare-graph.core"]')
    expect(graphs.find('[data-testid="self-reported"]').text()).toContain('Weak')
    expect(graphs.find('[data-testid="self-reported"]').text()).toContain('Recently studied')
    expect(graphs.find('[data-testid="observed"]').text()).toContain('Not measured yet')
  })
})
