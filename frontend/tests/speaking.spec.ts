import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { CommunicationReadiness, CompletionResult, ContentDetail, SpeakingResult } from '../src/api/types'
import { createMemoryHistory } from 'vue-router'
import { areaLabel, isCommunicationSkill } from '../src/presentation/communication'
import { createAppRouter } from '../src/router'
import { PREPARE_CATEGORIES, PREPARE_NAV, TRACK_OF_SLUG } from '../src/presentation/language'
import { skillsInCategory } from '../src/presentation/prepare'
import { serve } from './helpers'
import { summary } from './learningFixtures'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn() }))
vi.mock('../src/api', () => ({ api }))

import CommunicationReadinessPanel from '../src/components/learning/CommunicationReadiness.vue'
import ContentList from '../src/components/learning/ContentList.vue'
import SpeakingHistoryPanel from '../src/components/learning/SpeakingHistory.vue'
import SpeakingRunner from '../src/components/learning/SpeakingRunner.vue'
import SpeakingSignals from '../src/components/learning/SpeakingSignals.vue'
import type { RecognitionConstructor, RecognitionEventLike } from '../src/composables/useSpeechRecognition'
import { findRecognition, SPEECH_UNSUPPORTED, useSpeechRecognition } from '../src/composables/useSpeechRecognition'

class FakeRecognition {
  static last: FakeRecognition | null = null
  lang = ''
  continuous = false
  interimResults = false
  onresult: ((event: RecognitionEventLike) => void) | null = null
  onerror: ((event: { error: string }) => void) | null = null
  onend: (() => void) | null = null
  started = false
  constructor() {
    FakeRecognition.last = this
  }
  start(): void {
    this.started = true
  }
  stop(): void {
    this.started = false
    this.onend?.()
  }
  abort(): void {
    this.started = false
  }
  hear(parts: { text: string; final: boolean }[]): void {
    this.onresult?.({
      resultIndex: 0,
      results: Object.assign(
        parts.map((p) => ({ isFinal: p.final, 0: { transcript: p.text } })),
        { length: parts.length },
      ),
    })
  }
}
const FAKE = FakeRecognition as unknown as RecognitionConstructor

const PROMPT: ContentDetail = {
  ...summary('comm.speak_1m.practice', 'interview_question', {
    title: 'Describe a bug you fixed', skills: ['comm.speak_1m'], observation_kind: 'CONCEPT_EXPLAIN', stages: ['GUIDED'],
  }),
  body: {
    prompt: 'Describe a bug you fixed. Answer **aloud** in about a minute.',
    key_points: ['States the problem first'],
    speaking: { target_seconds: 60, min_words: 20, max_words: 150 },
    follow_ups: [{ prompt: 'How did you find it?', look_for: 'A concrete step.' }],
  },
  rubric: [{ key: 'p0', label: 'States the problem first', points: 1 }],
  pass_points: 70, problems: [], topic: null,
}

const SIGNALS: SpeakingResult = {
  source: 'BROWSER', metrics_version: 'speak-v1', word_count: 96, sentence_count: null, duration_seconds: 82,
  words_per_minute: 70, filler_count: 2, filler_per_100_words: 2, fillers: [['um', 1], ['you know', 1]],
  structure_markers: ['first', 'because'], vocabulary_used: ['root cause'], vocabulary_missing: ['rollback'],
  repeated_phrases: [], criteria: { fillers: 2, vocabulary: 1 }, evidence_note: 'Practice evidence from a browser transcript.',
}

beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-10-07T10:00:00Z'))
  vi.clearAllMocks()
  FakeRecognition.last = null
})
afterEach(() => vi.useRealTimers())

describe('useSpeechRecognition', () => {
  it('detects support from the window scope and reports none when absent', () => {
    expect(findRecognition({})).toBeNull()
    expect(findRecognition({ webkitSpeechRecognition: FAKE })).toBe(FAKE)
    expect(useSpeechRecognition(null).supported).toBe(false)
  })

  it('collects final text, shows interim text, measures the duration and stops on request', async () => {
    const speech = useSpeechRecognition(FAKE)
    speech.start()
    expect(speech.listening.value).toBe(true)
    FakeRecognition.last!.hear([{ text: 'we fixed the cache', final: true }, { text: 'and then', final: false }])
    expect(speech.transcript.value).toBe('we fixed the cache and then')
    vi.setSystemTime(new Date('2026-10-07T10:00:12Z'))
    speech.stop()
    expect(speech.elapsed.value).toBe(12)
    expect(speech.listening.value).toBe(false)
    expect(speech.final.value).toBe('we fixed the cache and then')
  })

  it('explains a blocked microphone in plain words', () => {
    const speech = useSpeechRecognition(FAKE)
    speech.start()
    FakeRecognition.last!.onerror?.({ error: 'not-allowed' })
    expect(speech.error.value).toContain('Microphone access was blocked')
  })
})

describe('SpeakingRunner', () => {
  const mountRunner = (recognition: RecognitionConstructor | null, result: CompletionResult | null = null) =>
    mount(SpeakingRunner, { props: { content: PROMPT, result, busy: false, recognition }, global: { stubs: { RouterLink: RouterLinkStub } } })

  it('discloses what the browser does and that no audio is stored', () => {
    const text = mountRunner(FAKE).get('[data-testid="speech-privacy"]').text()
    expect(text).toContain("browser's speech service")
    expect(text).toContain('does not store audio')
    expect(text).not.toMatch(/processed (entirely )?(locally|on your device)/i)
  })

  it('falls back to manual practice when the browser has no speech recognition', async () => {
    const wrapper = mountRunner(null)
    expect(wrapper.get('[data-testid="speech-unsupported"]').text()).toContain(SPEECH_UNSUPPORTED)
    expect(wrapper.find('[data-testid="start-speaking"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="manual-mode"]').exists()).toBe(true)
    await wrapper.get('input[name="criterion-p0"][value="2"]').setValue(true)
    await wrapper.get('[data-testid="submit-speaking"]').trigger('submit')
    const sent = wrapper.emitted('submit')![0]![0] as Record<string, unknown>
    expect(sent.speech).toEqual({ source: 'MANUAL', duration_seconds: 0 })
    expect(sent.ratings).toEqual({ p0: 2 })
    expect(sent).not.toHaveProperty('timed')
  })

  it('records a browser practice only after the transcript is reviewed, and sends no metrics or score', async () => {
    const wrapper = mountRunner(FAKE)
    expect(wrapper.get('[data-testid="submit-speaking"]').attributes('disabled')).toBeDefined()
    await wrapper.get('[data-testid="start-speaking"]').trigger('click')
    FakeRecognition.last!.hear([{ text: 'the root cause was a missing index', final: true }])
    await flushPromises()
    expect(wrapper.get('[data-testid="live-transcript"]').text()).toContain('missing index')
    vi.setSystemTime(new Date('2026-10-07T10:00:42Z'))
    await wrapper.get('[data-testid="stop-speaking"]').trigger('click')
    const box = wrapper.get('[data-testid="transcript"]')
    expect((box.element as HTMLTextAreaElement).value).toBe('the root cause was a missing index')
    await box.setValue('  the root cause was a missing index on orders  ')
    await wrapper.get('input[name="criterion-p0"][value="1"]').setValue(true)
    await wrapper.get('[data-testid="submit-speaking"]').trigger('submit')
    const sent = wrapper.emitted('submit')![0]![0] as Record<string, unknown>
    expect(sent.speech).toEqual({
      source: 'BROWSER', duration_seconds: 42, transcript: 'the root cause was a missing index on orders',
    })
    expect(JSON.stringify(sent)).not.toMatch(/word_count|filler|points|score/)
  })

  it('shows the server-measured signals for the transcript and surfaces a server rejection', async () => {
    api.post.mockResolvedValueOnce({ data: { speaking: SIGNALS }, meta: {} })
    const wrapper = mountRunner(FAKE)
    await wrapper.get('[data-testid="start-speaking"]').trigger('click')
    FakeRecognition.last!.hear([{ text: 'one two three four five six', final: true }])
    vi.setSystemTime(new Date('2026-10-07T10:00:10Z'))
    await wrapper.get('[data-testid="stop-speaking"]').trigger('click')
    await wrapper.get('[data-testid="check-signals"]').trigger('click')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/communication/preview', {
      content_key: 'comm.speak_1m.practice', transcript: 'one two three four five six', duration_seconds: 10,
    })
    expect(wrapper.get('[data-testid="speaking-signals"]').text()).toContain('96 words in 82 seconds')
  })
})

describe('Speaking result', () => {
  it('shows completion and signals, never a score or a follow-up number', async () => {
    const { default: ContentRunner } = await import('../src/components/learning/ContentRunner.vue')
    const result = {
      content_key: PROMPT.key, points: 100, passed: true, followup_points: 100, questions: [],
      observation: { kind: 'CONCEPT_EXPLAIN' }, progress: null, speaking: SIGNALS,
    } as unknown as CompletionResult
    const submit = vi.fn().mockResolvedValue({ result })
    const wrapper = mount(ContentRunner, { props: { content: PROMPT, submit }, global: { stubs: { RouterLink: RouterLinkStub } } })
    await wrapper.get('input[name="criterion-p0"][value="2"]').setValue(true)
    await wrapper.get('[data-testid="submit-speaking"]').trigger('submit')
    await flushPromises()
    const text = wrapper.get('[data-testid="completion-result"]').text()
    expect(text).toContain('Speaking practice completed.')
    expect(text).not.toMatch(/\/ 100|Follow-ups:|English score/)
  })
})

describe('SpeakingSignals', () => {
  it('describes signals without a grade, a percentage or a claim about grammar or pronunciation', () => {
    const text = mount(SpeakingSignals, { props: { speaking: SIGNALS } }).text()
    expect(text).toContain('96 words in 82 seconds (about 70 words per minute)')
    expect(text).toContain('2 filler words: um ×1, you know ×1')
    expect(text).toContain('Included 1 of 2 target phrases: root cause. Not used: rollback.')
    expect(text).toContain('Filler words: Fully')
    expect(text).not.toMatch(/\d+(\.\d+)?\s?%|score|grammar score|pronunciation/i)
  })

  it('says a manual practice measured no speech', () => {
    const manual = { ...SIGNALS, source: 'MANUAL' as const, duration_seconds: 0, criteria: {} }
    expect(mount(SpeakingSignals, { props: { speaking: manual } }).text()).toContain('No speech was measured.')
  })
})

describe('Communication Readiness panel', () => {
  const READY: CommunicationReadiness = {
    note: 'Communication Readiness is a separate, read-only view.',
    areas: [
      {
        key: 'comm.fluency', title: 'Fluency and confidence', status: 'DEVELOPING', status_label: 'Developing',
        summary: 'Developing: based on 5 measured speaking practices.', skills_total: 7, skills_with_evidence: 2,
        measured_rows: 5, manual_rows: 0, other_rows: 0, self_reported_only: 0, self_report: 'Self-reported: weak (context only, not measured)',
        skills: [{
          key: 'comm.speak_1m', name: 'Speak for 1 minute', score: 40, level: 3, confidence: 'LOW',
          measured: 5, manual: 0, other: 0, self_reported: false,
        }],
      },
      {
        key: 'comm.writing', title: 'Professional writing', status: 'NOT_STARTED', status_label: 'Not started',
        summary: 'Not measured yet.', skills_total: 4, skills_with_evidence: 0, measured_rows: 0, manual_rows: 0,
        other_rows: 0, self_reported_only: 0, self_report: null, skills: [],
      },
    ],
  }

  it('shows each area with the evidence it rests on and never an overall number', async () => {
    serve(api, { '/communication/readiness': READY })
    const wrapper = mount(CommunicationReadinessPanel, { global: { stubs: { RouterLink: RouterLinkStub } } })
    await vi.waitFor(() => expect(wrapper.find('[data-testid="comm-area-comm.fluency"]').exists()).toBe(true))
    expect(wrapper.get('[data-testid="comm-area-comm.fluency"]').text()).toContain('based on 5 measured speaking practices')
    expect(wrapper.get('[data-testid="comm-area-comm.writing"]').text()).toContain('Not measured yet.')
    expect(wrapper.get('[data-testid="comm-area-comm.fluency"]').text()).toContain('Self-reported: weak (context only')
    expect(wrapper.text()).toContain('separate, read-only view')
    expect(wrapper.text()).not.toMatch(/overall|\d+\s?%/i)
  })
})

describe('navigation', () => {
  it('adds Communication as a curriculum page without touching the scored areas', () => {
    expect(PREPARE_NAV.some((p) => p.slug === 'communication' && p.route === 'curriculum')).toBe(true)
    expect(TRACK_OF_SLUG.communication).toBe('communication')
    const router = createAppRouter(createMemoryHistory())
    expect(router.resolve({ name: 'curriculum', params: { slug: 'communication' } }).path).toBe('/prepare/communication')
    expect(router.resolve('/prepare/communication').name).toBe('curriculum')
    expect(TRACK_OF_SLUG.dsa).toBe('dsa')
  })
})

describe('communication never masquerades as a technical area', () => {
  const skills = [
    { key: 'arrays.traversal', component: 'dsa' },
    { key: 'python.core_syntax', component: 'coding' },
    { key: 'comm.speak_1m', component: 'coding' },
    { key: 'communication.structured_answers', component: 'behavioral' },
  ] as never[]

  it('keeps comm.* off the DSA page but keeps the required communication.* skills where they were', () => {
    const dsa = PREPARE_CATEGORIES.find((c) => c.slug === 'dsa')!
    const behavioral = PREPARE_CATEGORIES.find((c) => c.slug === 'behavioral')!
    expect(skillsInCategory(dsa, skills).map((s) => (s as { key: string }).key)).toEqual(['arrays.traversal', 'python.core_syntax'])
    expect(skillsInCategory(behavioral, skills).map((s) => (s as { key: string }).key)).toEqual(['communication.structured_answers'])
  })

  it('labels comm.* as Communication, never as Coding & Execution', () => {
    const labels = { coding: 'Coding & Execution' }
    expect(areaLabel('comm.speak_1m', 'coding', labels)).toBe('Communication')
    expect(areaLabel('python.core_syntax', 'coding', labels)).toBe('Coding & Execution')
    expect([isCommunicationSkill('comm.email'), isCommunicationSkill('communication.followup_handling')]).toEqual([true, false])
  })
})

describe('Speaking history panel', () => {
  it('labels every row as measured or manual and shows counts only', async () => {
    serve(api, {
      '/communication/history': {
        note: 'Transcripts and counts only; Master Mentor never stores audio.',
        rows: [
          { assessment_id: 2, skill: 'comm.speak_1m', skill_name: 'Speak for 1 minute', content_key: 'comm.speak_1m.practice',
            observed_on: '2026-10-06', source: 'MANUAL', duration_seconds: 20, word_count: 0, filler_count: 0,
            filler_per_100_words: null, timed: false, reference_used: true, reflection: null },
          { assessment_id: 1, skill: 'comm.speak_1m', skill_name: 'Speak for 1 minute', content_key: 'comm.speak_1m.practice',
            observed_on: '2026-10-05', source: 'BROWSER', duration_seconds: 55, word_count: 96, filler_count: 2,
            filler_per_100_words: 2, timed: true, reference_used: false, reflection: 'slower' },
        ],
      },
    })
    const wrapper = mount(SpeakingHistoryPanel, { global: { stubs: { RouterLink: RouterLinkStub } } })
    await vi.waitFor(() => expect(wrapper.find('.rows').exists()).toBe(true))
    const text = wrapper.text()
    expect(text).toContain('Manual self-review (weaker evidence)')
    expect(text).toContain('Measured from a browser transcript · 96 words in 55 s')
    expect(text).toContain('2 filler words per 100')
    expect(text).toContain('never stores audio')
    expect(wrapper.find('textarea').exists()).toBe(false)
  })

  it('never dead-ends when there is no practice yet', async () => {
    serve(api, { '/communication/history': { rows: [], note: 'n' } })
    const wrapper = mount(SpeakingHistoryPanel, { global: { stubs: { RouterLink: RouterLinkStub } } })
    await vi.waitFor(() => expect(wrapper.find('[data-testid="speaking-history-empty"]').exists()).toBe(true))
    expect(wrapper.text()).toContain('No speaking practice yet')
  })
})

describe('Content lists never show a score for a speaking practice', () => {
  const progress = { completions: 1, last_points: 82, best_points: 82, last_on: '2026-10-05', passed: true, milestones_done: [], defended: false }
  it('shows Practised for spoken items and the number for everything else', () => {
    const items = [
      { ...summary('comm.speak_1m.practice', 'interview_question'), spoken: true, progress },
      { ...summary('dsa.complexity.exercise', 'coding_exercise'), progress },
    ]
    const text = mount(ContentList, { props: { items }, global: { stubs: { RouterLink: RouterLinkStub } } }).text()
    expect(text).toContain('Practised')
    expect(text).toContain('82')
    expect(text.match(/82/g)).toHaveLength(1)  // only the technical item shows its number
  })
})
