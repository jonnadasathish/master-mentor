import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ApiClient } from '../src/api/client'
import AssessmentForm from '../src/components/practice/AssessmentForm.vue'
import SkillDeltas from '../src/components/missions/SkillDeltas.vue'
import { assessmentErrors, buildAssessmentPayload, buildSweepPayload, emptyAssessmentForm } from '../src/practice/assessment'

beforeEach(() => setActivePinia(createPinia()))

const stubs = { RouterLink: RouterLinkStub }

describe('assessment payload', () => {
  it('sends only observed skills and converts minutes to seconds', () => {
    const form = emptyAssessmentForm('battery:M0-B04', ['db.indexing', 'db.transactions'])
    form.points['db.indexing'] = 70
    form.timed = true
    form.limitMinutes = 20
    form.minutes = 18
    expect(assessmentErrors(form)).toEqual([])
    expect(buildAssessmentPayload('RECALL_QUIZ', form, 'req-12345678', 'M0-B04')).toEqual({
      kind: 'RECALL_QUIZ',
      source_key: 'battery:M0-B04',
      notes_used: false,
      reference_used: false,
      hints_used: 0,
      timed: true,
      time_limit_seconds: 1200,
      time_seconds: 1080,
      skills: [{ skill: 'db.indexing', outcome_points: 70 }],
      battery_item_key: 'M0-B04',
      mode: 'BASELINE',
      client_request_id: 'req-12345678',
    })
  })

  it('treats emptied number inputs as not given and rejects out-of-range points', () => {
    const form = emptyAssessmentForm('k', ['a'])
    ;(form.points as Record<string, unknown>).a = ''
    expect(assessmentErrors(form)).toContain('Score at least one skill (0–100).')
    form.points.a = 140
    expect(assessmentErrors(form)).toContain('Points must be 0–100.')
  })

  it('builds the familiarity sweep from answered skills only', () => {
    expect(buildSweepPayload({ a: 'NONE', b: null, c: 'SOLID' }, 'sweep-1234')).toEqual({
      entries: [{ skill: 'a', familiarity: 'NONE' }, { skill: 'c', familiarity: 'SOLID' }],
      client_request_id: 'sweep-1234',
    })
  })
})

describe('SkillDeltas', () => {
  it('shows backend before/after values without computing anything', () => {
    const wrapper = mount(SkillDeltas, {
      global: { stubs },
      props: {
        deltas: [
          { skill_key: 'graph.traversal', before: null, after: { score: 26, effective: 11, level: 1, confidence: 'LOW' } },
        ],
      },
    })
    expect(wrapper.text()).toMatch(/Traversal\s*not measured yet → 26\s*· low confidence/)
    expect(wrapper.text()).not.toContain('graph.traversal')
  })

  it('says so when nothing changed', () => {
    expect(mount(SkillDeltas, { global: { stubs }, props: { deltas: [] } }).text()).toBe('No skill score changed.')
  })
})

describe('AssessmentForm', () => {
  it('posts the assessment and shows the resulting deltas', async () => {
    const post = vi.fn().mockResolvedValue({
      data: { id: 3 },
      meta: {},
      effects: { run_id: 9, skill_deltas: [{ skill_key: 'db.indexing', before: null, after: { score: 26, effective: 11, level: 1, confidence: 'LOW' } }] },
    })
    const client: ApiClient = { get: vi.fn() as ApiClient['get'], post }
    const wrapper = mount(AssessmentForm, {
      global: { stubs },
      props: { client, kind: 'RECALL_QUIZ', skills: [{ key: 'db.indexing', name: 'Indexing' }], sourceKey: 'battery:M0-B04', batteryItemKey: 'M0-B04' },
    })
    await wrapper.find('[data-testid="points-db.indexing"]').setValue('80')
    await wrapper.find('[data-testid="assessment-form"]').trigger('submit')
    await flushPromises()
    expect(post).toHaveBeenCalledOnce()
    expect(post.mock.calls[0]![1]).toMatchObject({ kind: 'RECALL_QUIZ', skills: [{ skill: 'db.indexing', outcome_points: 80 }], battery_item_key: 'M0-B04' })
    expect(wrapper.find('[data-testid="assessment-recorded"]').exists()).toBe(true)
    expect(wrapper.text()).toMatch(/Indexing\s*not measured yet → 26\s*· low confidence/)
  })

  it('blocks submission with client-side errors', async () => {
    const post = vi.fn()
    const client: ApiClient = { get: vi.fn() as ApiClient['get'], post }
    const wrapper = mount(AssessmentForm, {
      global: { stubs },
      props: { client, kind: 'CONCEPT_EXPLAIN', skills: [{ key: 'x', name: 'X' }], sourceKey: 'prompt:x' },
    })
    await wrapper.find('[data-testid="assessment-form"]').trigger('submit')
    expect(post).not.toHaveBeenCalled()
    expect(wrapper.find('[data-testid="assessment-errors"]').text()).toContain('Score at least one skill')
  })
})
