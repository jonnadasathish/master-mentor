import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { parseBlocks } from '../src/presentation/richtext'
import { GAP_DETAIL, SKILLS, skill } from './fixtures'
import { serve } from './helpers'
import {
  CHECK, CHECK_RESULT, CONCEPT_ONLY, EXERCISE, LESSON, SESSION, SKILL_DETAIL, STUDY_RESULT, TRACK, UNCOVERED, learning,
} from './learningFixtures'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn() }))
const route = vi.hoisted(() => ({ params: {} as Record<string, string>, query: {} as Record<string, string>, path: '/' }))
const push = vi.hoisted(() => vi.fn())
vi.mock('../src/api', () => ({ api }))
vi.mock('vue-router', async (orig) => ({ ...(await orig<object>()), useRoute: () => route, useRouter: () => ({ push }) }))

import CurriculumSection from '../src/components/learning/CurriculumSection.vue'
import ProblemsView from '../src/views/dsa/ProblemsView.vue'
import LearnContentView from '../src/views/learn/LearnContentView.vue'
import LearningSessionView from '../src/views/learn/LearningSessionView.vue'
import SkillDetailView from '../src/views/SkillDetailView.vue'

const stubs = { RouterLink: RouterLinkStub }

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  route.params = {}
  route.query = {}
})

async function settle(wrapper: ReturnType<typeof mount>, selector: string) {
  await vi.waitFor(() => expect(wrapper.find(selector).exists()).toBe(true))
  await flushPromises()
}
const linkTo = (wrapper: ReturnType<typeof mount>, testid: string) =>
  wrapper.findAllComponents(RouterLinkStub).find((c) => c.attributes('data-testid') === testid)?.props('to')

describe('content text', () => {
  it('parses the safe subset and never treats markup as HTML', () => {
    const blocks = parseBlocks('First `code` and **bold**.\n\n- one\n- two\n\n```python\nx = 1\n```\n\n1. a\n2. b')
    expect(blocks.map((b) => b.kind)).toEqual(['p', 'ul', 'code', 'ol'])
    expect(blocks[0]).toEqual({ kind: 'p', inlines: [
      { kind: 'text', text: 'First ' }, { kind: 'code', text: 'code' }, { kind: 'text', text: ' and ' }, { kind: 'bold', text: 'bold' },
      { kind: 'text', text: '.' }] })
    expect(blocks[2]).toEqual({ kind: 'code', language: 'python', code: 'x = 1' })
  })
})

describe('Skill page learning (no dead ends)', () => {
  async function open(model: unknown, key = 'graph.traversal') {
    route.params = { key }
    serve(api, {
      '/skills': [...SKILLS, skill('recursion.fundamentals', 'Recursion'), skill('graph.representation', 'Graph representation')],
      [`/skills/${key}`]: { ...SKILL_DETAIL, key },
      [`/gaps/${key}`]: GAP_DETAIL,
      [`/skills/${key}/learning`]: model,
    })
    const wrapper = mount(SkillDetailView, { global: { stubs } })
    await settle(wrapper, '[data-testid="skill-learning"]')
    return wrapper
  }

  it('explains why the skill matters and offers Learn / Practice / Test / Revise', async () => {
    const wrapper = await open(learning())
    const why = wrapper.find('[data-testid="why-it-matters"]').text()
    expect(why).toContain('Critical for your target role')
    expect(why).toContain('tested in DSA rounds')
    expect(why).toContain('1 skill builds on it')
    expect(wrapper.findAll('[role="tab"]').map((t) => t.text().replace(/\s+\d+$/, ''))).toEqual(['Learn', 'Practice', 'Test', 'Revise'])
    await wrapper.find('[data-testid="tab-practice"]').trigger('click')
    expect(wrapper.find('[data-testid="practice-case"]').text()).toContain('directly')
    expect(wrapper.find('[data-testid="direct-problems"]').text()).toContain('Solved with a hint')
    expect(linkTo(wrapper, 'start-practice')).toEqual({ name: 'problems', query: { skill: 'graph.traversal' } })
  })

  it('starts a learning session from the mentor stage and opens it', async () => {
    api.post.mockResolvedValue({ data: { ...SESSION, id: 9 }, meta: {} })
    const wrapper = await open(learning())
    const preview = wrapper.find('[data-testid="next-action"]').text()
    expect(preview).toContain('The mentor picked this stage from your evidence.')
    expect(preview).toContain('Number of Islands')
    await wrapper.find('[data-testid="start-session"]').trigger('click')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/learning/sessions', { skill: 'graph.traversal', stage: 'PATTERN_DRILL' })
    expect(push).toHaveBeenCalledWith({ name: 'session', params: { id: 9 } })
  })

  it('a concept skill is practised by checks and questions, never sent to an empty problem list', async () => {
    const wrapper = await open(CONCEPT_ONLY, 'dsa.complexity_analysis')
    await wrapper.find('[data-testid="tab-practice"]').trigger('click')
    expect(wrapper.find('[data-testid="practice-case"]').text()).toContain('concept skill')
    expect(wrapper.find('[data-testid="related-problems"]').text()).toContain('via Hashing (uses this skill)')
    expect(linkTo(wrapper, 'start-practice')).toMatchObject({ name: 'log', query: { skill: 'dsa.complexity_analysis' } })
  })

  it('an uncovered skill says so honestly and still gives a next action', async () => {
    const wrapper = await open(UNCOVERED)
    const gap = wrapper.find('[data-testid="content-gap"]')
    expect(gap.text()).toContain('Meanwhile, practise')
    expect(gap.findAllComponents(RouterLinkStub).map((l: { props: (k: string) => unknown }) => l.props('to'))).toEqual([
      { name: 'skill', params: { key: 'recursion.fundamentals' } },
      { name: 'log', query: { skill: 'graph.traversal' } },
    ])
    expect(wrapper.find('[data-testid="start-session"]').exists()).toBe(false)
  })

  it('still works when the learning layer is unavailable', async () => {
    route.params = { key: 'graph.traversal' }
    serve(api, { '/skills': SKILLS, '/skills/graph.traversal': SKILL_DETAIL, '/gaps/graph.traversal': GAP_DETAIL })
    const wrapper = mount(SkillDetailView, { global: { stubs } })
    await settle(wrapper, '[data-testid="skill-focus"]')
    expect(wrapper.find('[data-testid="skill-learning"]').exists()).toBe(false)
    expect(linkTo(wrapper, 'start-practice')).toEqual({ name: 'problems', query: { skill: 'graph.traversal' } })
  })
})

describe('Problem list for a skill without problems', () => {
  it('shows related practice instead of "No problems match."', async () => {
    route.query = { skill: 'dsa.complexity_analysis' }
    serve(api, { '/problems': [], '/skills': SKILLS, '/catalog/skills': [], '/skills/dsa.complexity_analysis/learning': CONCEPT_ONLY })
    const wrapper = mount(ProblemsView, { global: { stubs } })
    await settle(wrapper, '[data-testid="practice-fallback"]')
    expect(wrapper.text()).not.toContain('No problems match.')
    expect(wrapper.find('[data-testid="related-problems"]').text()).toContain('Two Sum')
    // the problem page resolves the full key (platform:slug), as every other problem link does
    expect(wrapper.findAllComponents(RouterLinkStub).some((l) => JSON.stringify(l.props('to')) === JSON.stringify({ name: 'problem', params: { problemKey: 'LEETCODE:two-sum' } }))).toBe(true)
    expect(wrapper.find('[data-testid="fallback-content"]').exists()).toBe(true)
    expect(linkTo(wrapper, 'open-skill')).toEqual({ name: 'skill', params: { key: 'dsa.complexity_analysis' } })
  })
})

describe('Learning content', () => {
  async function openContent(detail: unknown, key: string) {
    route.params = { key }
    serve(api, { [`/learning/content/${key}`]: detail, '/skills': SKILLS })
    const wrapper = mount(LearnContentView, { global: { stubs } })
    await settle(wrapper, '[data-testid="content-title"]')
    return wrapper
  }

  it('a lesson reads in order, renders code safely and records study time', async () => {
    api.post.mockResolvedValue({ data: STUDY_RESULT, meta: {}, effects: { run_id: 1, skill_deltas: [] } })
    const wrapper = await openContent(LESSON, 'dsa.complexity.lesson')
    const sections = wrapper.findAll('[data-section]').map((s) => s.attributes('data-section'))
    expect(sections.slice(0, 5)).toEqual(['what', 'why', 'when', 'how', 'mental_model'])
    expect(wrapper.find('[data-section="what"]').text()).toContain('<script>alert(1)</script> stays text')
    expect(wrapper.find('script').exists()).toBe(false)
    expect(wrapper.find('[data-section="how"] code').text()).toBe('O(n)')
    await wrapper.find('[data-testid="mark-studied"]').trigger('click')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith(
      '/learning/content/dsa.complexity.lesson/complete', expect.objectContaining({ minutes: 10 }))
    expect(wrapper.find('[data-testid="completion-result"]').text()).toContain('Recorded as study time.')
  })

  it('a concept check sends answers for grading and then explains every question', async () => {
    api.post.mockResolvedValue({ data: CHECK_RESULT, meta: {}, effects: { run_id: 1, skill_deltas: [] } })
    const wrapper = await openContent(CHECK, 'dsa.complexity.check')
    await wrapper.find('[data-testid="question-q1"] input[type="radio"]:nth-of-type(1)').trigger('change')
    const radios = wrapper.findAll('[data-testid="question-q1"] input')
    await radios[1]!.trigger('change')
    await wrapper.findAll('[data-testid="question-q2"] input')[0]!.trigger('change')
    await wrapper.find('[data-testid="reveal-q3"]').trigger('click')
    expect(wrapper.find('[data-testid="question-q3"]').text()).toContain('Too slow; aim for O(n log n).')
    await wrapper.findAll('[data-testid="rate-grade-q3"] input')[2]!.trigger('change')
    await wrapper.find('[data-testid="check-runner"]').trigger('submit')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/learning/content/dsa.complexity.check/complete', expect.objectContaining({
      answers: { q1: [1], q2: [0] }, self_grades: { q3: 2 }, notes_used: false,
    }))
    expect(wrapper.findAll('[data-testid="explanation"]')).toHaveLength(3)
    expect(wrapper.text()).toContain('pop() is O(1) too.')
    expect(wrapper.find('[data-testid="completion-result"]').text()).toContain('67 / 100')
  })

  it('practice counts hints and the reference honestly and sends the rubric', async () => {
    api.post.mockResolvedValue({ data: { ...CHECK_RESULT, points: 71, questions: [] }, meta: {}, effects: { run_id: 1, skill_deltas: [] } })
    const wrapper = await openContent(EXERCISE, 'dsa.complexity.exercise')
    expect(wrapper.find('[data-testid="practice-timer"]').exists()).toBe(true)
    await wrapper.find('[data-testid="show-hint"]').trigger('click')
    expect(wrapper.find('[data-testid="hints"]').text()).toContain('Count complements.')
    await wrapper.find('[data-testid="show-reference"]').trigger('click')
    await wrapper.findAll('[data-testid="rate-criterion-correct"] input')[2]!.trigger('change')
    await wrapper.findAll('[data-testid="rate-followup-0"] input')[1]!.trigger('change')
    await wrapper.find('[data-testid="practice-runner"]').trigger('submit')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/learning/content/dsa.complexity.exercise/complete', expect.objectContaining({
      ratings: { correct: 2 }, followups: { '0': 1 }, hints_used: 1, reference_used: true,
    }))
  })
})

describe('Learning session', () => {
  it('walks the steps, records each through the session, and ends with before/after', async () => {
    route.params = { id: '5' }
    serve(api, {
      '/learning/sessions/5': SESSION, '/learning/content/dsa.complexity.lesson': LESSON, '/learning/content/dsa.complexity.check': CHECK,
      '/skills': SKILLS,
    })
    const afterLesson = { ...SESSION, next_position: 2, steps: SESSION.steps.map((s) => (s.position === 1 ? { ...s, status: 'DONE' as const } : s)) }
    api.post.mockResolvedValueOnce({ data: { session: afterLesson, completion: STUDY_RESULT, attempt_id: null }, meta: {}, effects: { run_id: 2, skill_deltas: [] } })
    const wrapper = mount(LearningSessionView, { global: { stubs } })
    await settle(wrapper, '[data-testid="lesson"]')
    expect(wrapper.find('[data-testid="session-steps"]').text()).toContain('Concept check')
    await wrapper.find('[data-testid="mark-studied"]').trigger('click')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/learning/sessions/5/steps/1/complete', { completion: expect.objectContaining({ minutes: 10 }) })
    await wrapper.find('[data-testid="next-step"]').trigger('click')
    await settle(wrapper, '[data-testid="check-runner"]')

    const done = { ...SESSION, status: 'COMPLETED' as const, outcome: 'PASSED' as const, next_position: null,
      before: { score: null, level: null }, after: { score: 24, level: 1 } }
    api.post.mockResolvedValueOnce({ data: done, meta: {} })
    await wrapper.find('[data-testid="skip-step"]').trigger('click')
    await flushPromises()
    expect(api.post).toHaveBeenLastCalledWith('/learning/sessions/5/steps/2/skip', {})
    expect(wrapper.find('[data-testid="before-after"]').text()).toBe('Score not measured → 24')
    expect(wrapper.find('[data-testid="session-summary"]').text()).toContain('Every scored step passed.')
  })
})

describe('Curriculum', () => {
  it('lists topics in teaching order with skills, score/target, coverage and their content', async () => {
    serve(api, { '/learning/tracks/dsa': TRACK })
    const wrapper = mount(CurriculumSection, { props: { track: 'dsa' }, global: { stubs } })
    await settle(wrapper, '[data-testid="topic-dsa.method"]')
    const topic = wrapper.find('[data-testid="topic-dsa.method"]').text()
    expect(topic).toContain('Problem-solving method')
    expect(topic).toContain('Complexity analysis')
    expect(topic).toContain('— / 80')
    expect(topic).toContain('Partial path')
    expect(wrapper.text()).toContain('1 of 3 items done')
    await wrapper.find('[data-testid="topic-toggle-dsa.method"]').trigger('click')
    expect(wrapper.find('[data-testid="topic-content-dsa.method"]').text()).toContain('Title of dsa.complexity.check')
  })
})

describe('Today missions open their learning session', () => {
  it('shows the steps a mission contains and starts the session linked to the plan item', async () => {
    const { default: MissionCard } = await import('../src/components/missions/MissionCard.vue')
    const { missionText } = await import('../src/presentation/mission')
    const { planItem, baseline } = await import('./fixtures')
    api.post.mockResolvedValue({ data: { ...SESSION, id: 12 }, meta: {} })
    const item = planItem()
    const ctx = { nameOf: (k: string) => k, componentOf: () => 'dsa', battery: baseline(0).items }
    const learningPreview = {
      stage: 'PATTERN_DRILL', minutes: 38, session_id: null,
      steps: [{ position: 1, kind: 'CONTENT' as const, title: 'Pattern quiz', minutes: 8, content_key: 'dsa.patterns.quiz',
        content_type: 'quiz' as const, problem_id: null }],
    }
    const client = { get: vi.fn(), post: vi.fn(), patch: vi.fn() }
    const wrapper = mount(MissionCard, {
      global: { stubs },
      props: { item, client: client as never, text: missionText(item, ctx), learning: learningPreview },
    })
    expect(wrapper.find('[data-testid="session-preview-1"]').text()).toContain('Pattern quiz')
    expect(wrapper.find('[data-testid="start-1"]').text()).toContain('Do it my way')
    await wrapper.find('[data-testid="open-session-1"]').trigger('click')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/learning/sessions', { skill: 'graph.traversal', stage: 'PATTERN_DRILL', plan_item_id: 7 })
    expect(push).toHaveBeenCalledWith({ name: 'session', params: { id: 12 } })
  })
})

describe('Mock kits', () => {
  it('offers rehearsal prompts per round with the skills to probe first', async () => {
    const { default: MockKits } = await import('../src/components/learning/MockKits.vue')
    const { summary } = await import('./learningFixtures')
    serve(api, {
      '/learning/mock-kits': [
        { round: 'DSA_1', round_type: 'DSA', minutes: 45, components: ['dsa'], items: [summary('dsa.x.q', 'interview_question', { time_limit_seconds: 600 })],
          focus_skills: [{ key: 'graph.traversal', name: 'Graphs', status: 'CRITICAL' }] },
        { round: 'SYSTEM_DESIGN', round_type: 'SYSTEM_DESIGN', minutes: 45, components: ['system_design'], items: [], focus_skills: [] },
      ],
    })
    const wrapper = mount(MockKits, { global: { stubs } })
    await settle(wrapper, '[data-testid="mock-kits"]')
    expect(wrapper.text()).toContain('Probe first:')
    expect(wrapper.find('[data-testid="kit-items-DSA_1"]').text()).toContain('Title of dsa.x.q')
    await wrapper.find('[data-testid="kit-SYSTEM_DESIGN"]').trigger('click')
    expect(wrapper.text()).toContain('No timed prompts for this round in the library yet.')
  })
})

describe('Coverage report (Developer / System)', () => {
  it('summarises states for required skills and filters the table', async () => {
    const { default: CoverageView } = await import('../src/views/settings/CoverageView.vue')
    const row = (key: string, state: 'FULL' | 'CONTENT_GAP', required = true) => ({
      skill_key: key, skill_name: key, component: 'dsa', tracks: ['dsa'], tier: required ? 'T1' : 'T4', importance: 100, required,
      direct_learning_content: state === 'FULL' ? 1 : 0, concept_checks: 0, practice_count: 0, timed_practice: 0, revision_content: 0,
      mock_coverage: ['DSA'], coverage_state: state,
    })
    serve(api, { '/learning/coverage': {
      summary: { all: { FULL: 1, PARTIAL: 0, UNMEASURED: 0, CONTENT_GAP: 2 }, required: { FULL: 1, PARTIAL: 0, UNMEASURED: 0, CONTENT_GAP: 1 } },
      content_counts: { lesson: 3, quiz: 0 },
      rows: [row('a.full', 'FULL'), row('b.gap', 'CONTENT_GAP'), row('c.optional', 'CONTENT_GAP', false)],
    } })
    const wrapper = mount(CoverageView, { global: { stubs } })
    await settle(wrapper, '[data-testid="coverage-table"]')
    expect(wrapper.findAll('tbody tr')).toHaveLength(2) // required only by default
    await wrapper.find('[data-testid="coverage-filter"]').setValue('CONTENT_GAP')
    expect(wrapper.findAll('tbody tr').map((r) => r.text())).toEqual([expect.stringContaining('b.gap')])
    expect(wrapper.text()).toContain('3 Lesson')
  })
})
