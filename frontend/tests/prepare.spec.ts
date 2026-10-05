import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { baseline, calibrationToday, personalRoadmap, skill, GAP_DETAIL, HISTORY, planItem, READINESS, revisionItem, revisionList, ROADMAP, SKILL_DETAIL, SKILLS, today, WEEK } from './fixtures'
import { serve } from './helpers'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn() }))
const route = vi.hoisted(() => ({ params: {} as Record<string, string>, query: {} as Record<string, string>, path: '/' }))
vi.mock('../src/api', () => ({ api }))
vi.mock('vue-router', async (orig) => ({ ...(await orig<object>()), useRoute: () => route }))

import DsaView from '../src/views/DsaView.vue'
import PrepareView from '../src/views/PrepareView.vue'
import RoadmapView from '../src/views/RoadmapView.vue'
import SkillDetailView from '../src/views/SkillDetailView.vue'
import TrackView from '../src/views/TrackView.vue'

const stubs = { RouterLink: RouterLinkStub }

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  route.params = {}
  route.query = {}
})

const base = {
  '/skills': SKILLS, '/readiness': READINESS, '/readiness/history': HISTORY, '/baseline': { ...baseline(12), calibration_mode: false },
  '/today': today(), '/today/week': WEEK, '/revisions': revisionList([revisionItem('PATTERN:graph.traversal', 'overdue')]),
  '/problem-attempts': [], '/problems': [], '/catalog/skills': [],
}
async function settle(wrapper: ReturnType<typeof mount>, selector: string) {
  await vi.waitFor(() => expect(wrapper.find(selector).exists()).toBe(true))
  await flushPromises()
}

describe('Prepare hub', () => {
  it('shows each area with its score against the level needed, its top gap and the next step', async () => {
    serve(api, base)
    const wrapper = mount(PrepareView, { global: { stubs } })
    await settle(wrapper, '[data-testid="category-dsa"]')
    expect(wrapper.findAll('[data-testid^="category-"]')).toHaveLength(5)
    const dsa = wrapper.find('[data-testid="category-dsa"]').text()
    expect(dsa).toContain('DSA')
    expect(dsa).toContain('78')
    expect(dsa).toContain('72 needed')
    expect(dsa).toContain('Graphs: BFS and DFS')
    expect(dsa).toContain('Next Pattern drill · Graphs: BFS and DFS')
    expect(dsa).toContain('Critical')
    const sd = wrapper.find('[data-testid="category-system-design"]').text()
    expect(sd).toContain('54')
    expect(sd).toContain('Guided practice · Caching strategies')
    expect(wrapper.find('[data-testid="finish-baseline"]').exists()).toBe(false)
  })

  it('sends you to finish the baseline first while calibrating, and says unmeasured areas are unmeasured', async () => {
    serve(api, { ...base, '/baseline': baseline(2), '/readiness': { ...READINESS, components: READINESS.components.map((c) => ({ ...c, assessed_pct: 0, score: 0 })) } })
    const wrapper = mount(PrepareView, { global: { stubs } })
    await settle(wrapper, '[data-testid="finish-baseline"]')
    expect(wrapper.find('[data-testid="finish-baseline"]').text()).toContain('2 of 12 assessments done')
    expect(wrapper.find('[data-testid="category-dsa"]').text()).toContain('Not measured yet')
  })
})

describe('Track view', () => {
  it('summarises one area, lists its gaps and keeps the full skill list collapsed', async () => {
    serve(api, base)
    route.params = { slug: 'system-design' }
    const wrapper = mount(TrackView, { global: { stubs } })
    await settle(wrapper, '[data-testid="toggle-all"]')
    expect(wrapper.find('h1').text()).toBe('System Design')
    expect(wrapper.text()).toContain('54')
    expect(wrapper.text()).toContain('Guided practice: Caching strategies')
    expect(wrapper.find('[data-testid="top-gaps"]').text()).toContain('Caching strategies')
    expect(wrapper.find('[data-testid="all-skills"]').exists()).toBe(false)
    await wrapper.find('[data-testid="toggle-all"]').trigger('click')
    expect(wrapper.find('[data-testid="all-skills"]').text()).toContain('Caching strategies')
  })
})

describe('DSA view', () => {
  it("shows today's DSA missions, weak spots, recent attempts, reviews and progress by pattern", async () => {
    const attempt = { id: 8, problem: { id: 17, key: 'LEETCODE:number-of-islands', title: 'Number of Islands', difficulty: 'MEDIUM', source: 'CATALOG' }, attempted_on: '2026-10-04', outcome: 'FAIL' }
    serve(api, {
      ...base, '/problem-attempts': [attempt],
      '/catalog/skills': [{ key: 'graph.traversal', name: 'Graphs: BFS and DFS', group: 'g', component: 'dsa', is_pattern: true, tier: 'T1', required: true }],
      '/today': today({}, [planItem(), planItem({ id: 9, position: 2, candidate_type: 'GAP', skill: 'sd.caching', problems: [], candidate_key: 'GAP:sd.caching' })]),
    })
    const wrapper = mount(DsaView, { global: { stubs } })
    await settle(wrapper, '[data-testid="patterns"]')
    expect(wrapper.find('h1').text()).toBe('DSA')
    expect(wrapper.find('[data-testid="dsa-today"]').findAll('li')).toHaveLength(1)
    expect(wrapper.find('[data-testid="dsa-today"]').text()).toContain('Pattern drill')
    expect(wrapper.find('[data-testid="top-gaps"]').text()).toContain('Graphs: BFS and DFS')
    expect(wrapper.find('[data-testid="recent-attempts"]').text()).toContain('Number of Islands')
    expect(wrapper.find('[data-testid="recent-attempts"]').text()).toContain('Failed')
    expect(wrapper.text()).toContain('Reviews waiting')
    expect(wrapper.find('[data-testid="patterns"]').text()).toContain('43 / 80')
    expect(wrapper.find('[data-testid="browse-problems"]').exists()).toBe(true)
  })

  it('says so when there is nothing to do', async () => {
    serve(api, { ...base, '/today': calibrationToday(0, []), '/revisions': revisionList([]) })
    const wrapper = mount(DsaView, { global: { stubs } })
    await settle(wrapper, '[data-testid="browse-problems"]')
    expect(wrapper.text()).toContain('No DSA mission today.')
    expect(wrapper.text()).toContain("You're clear for today.")
  })
})

describe('Skill detail', () => {
  async function open(detail = SKILL_DETAIL) {
    route.params = { key: 'graph.traversal' }
    serve(api, {
      ...base,
      '/skills': [...SKILLS, skill('recursion.fundamentals', 'Recursion'), skill('graph.representation', 'Graph representation')],
      '/skills/graph.traversal': detail,
      '/gaps/graph.traversal': GAP_DETAIL,
    })
    const wrapper = mount(SkillDetailView, { global: { stubs } })
    await settle(wrapper, '[data-testid="skill-focus"]')
    return wrapper
  }

  it('explains the skill: score, status, confidence, evidence, why it is weak, prerequisites and the next action', async () => {
    const wrapper = await open()
    expect(wrapper.find('[data-testid="skill-name"]').text()).toBe('Graphs: BFS and DFS')
    const tiles = wrapper.find('[data-testid="skill-state"]').text()
    expect(tiles).toContain('43')
    expect(tiles).toContain('/ 80')
    expect(tiles).toContain('Critical')
    expect(tiles).toContain('Medium')
    expect(tiles).toContain('12 observations')

    const why = wrapper.find('[data-testid="skill-gap"]').text()
    expect(why).toContain('Pattern recognition.')
    expect(why).toContain('3 of your last 5 attempts failed.')
    expect(why).toContain('You missed the pattern in 3 of your last 4 attempts.')
    expect(why).toContain('You last practised this 12 days ago.')
    expect(why).toContain('DSA overall is at 58; it needs 72.')

    const text = wrapper.text()
    expect(text).toContain('Recursion')
    expect(text).toContain('Graph representation')
    expect(text).toContain("needs 60, you're at 42")
    expect(wrapper.find('svg[aria-label="Ready"]').exists()).toBe(true)
    expect(wrapper.find('svg[aria-label="Needs work"]').exists()).toBe(true)

    const focus = wrapper.find('[data-testid="skill-focus"]')
    expect(focus.text()).toContain('Pattern drill: Graphs: BFS and DFS')
    expect(focus.text()).toContain('25 min')
    expect(focus.text()).toContain('a score of 70 or more')
    const start = wrapper.findAllComponents(RouterLinkStub).find((c) => c.attributes('data-testid') === 'start-practice')
    expect(start?.props('to')).toEqual({ name: 'problems', query: { skill: 'graph.traversal' } })

    const timeline = wrapper.find('[data-testid="evidence-table"]').text()
    expect(timeline).toContain('Practice attempt')
    expect(timeline).toContain('Scored 40')
    expect(timeline).toContain('Recall quiz')
    expect(timeline).not.toMatch(/R1|rule|level/i)
  })

  it('shows a declared-unknown skill as measured at zero in plain words', async () => {
    const wrapper = await open({ ...SKILL_DETAIL, state: { ...SKILL_DETAIL.state, declared_unknown: true } })
    expect(wrapper.text()).toContain('You told us this is new to you')
  })
})

describe('Roadmap: planned order', () => {
  async function planned(skillsList = SKILLS) {
    serve(api, { '/roadmap': ROADMAP, '/skills': skillsList, '/roadmap/personal': personalRoadmap() })
    const wrapper = mount(RoadmapView, { global: { stubs } })
    await settle(wrapper, '[data-testid="personal-roadmap"]')
    await wrapper.find('[data-testid="view-planned"]').trigger('click')
    await settle(wrapper, '[data-testid="roadmap"]')
    return wrapper
  }

  it('puts the roadmap order beside the mentor priority and says when they agree', async () => {
    const wrapper = await planned()
    const compare = wrapper.find('[data-testid="roadmap-vs-priority"]').text()
    expect(compare).toContain('Next on the roadmap: Core patterns')
    expect(compare).toContain('Graphs: BFS and DFS')
    expect(compare).toContain('The roadmap and your priorities agree.') // graph.traversal is in the current milestone
  })

  it('flags a difference and shows current, completed and upcoming milestones', async () => {
    const other = SKILLS.map((s) => (s.key === 'graph.traversal' ? { ...s, gap: { ...s.gap!, status: 'NONE' } } : s))
    const wrapper = await planned(other)
    expect(wrapper.find('[data-testid="roadmap-vs-priority"]').text()).toContain('They differ, and that\'s intended')
    const current = wrapper.find('[data-testid="milestone-DSA-2"]').text()
    expect(current).toContain('Current milestone')
    expect(current).toContain('6 of 21 core skills ready')
    expect(current).toContain('10 timed problems')
    expect(wrapper.text()).toContain('1 completed')
    expect(wrapper.find('[data-testid="milestone-DSA-3"]').text()).toContain('Advanced graphs, tries, DP')
    await wrapper.find('[data-testid="track-cs"]').trigger('click')
    expect(wrapper.find('[data-testid="milestone-CS-1"]').text()).toContain('DBMS')
  })
})
