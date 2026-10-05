import type {
  AssessmentRecord, CompletionResult, ContentDetail, ContentSummary, LearningSession, LearningTrackDetail, SkillLearning,
} from '../src/api/types'
import { SKILL_DETAIL } from './fixtures'

/** Learning-layer fixtures typed against the API contract (API_SPEC §11). */
export function summary(key: string, type: ContentSummary['type'], extra: Partial<ContentSummary> = {}): ContentSummary {
  const tab = type === 'concept_check' || type === 'quiz' || type === 'interview_question' ? 'test'
    : type === 'revision_card' ? 'revision' : ['lesson', 'concept', 'worked_example', 'visual_explanation'].includes(type) ? 'learn' : 'practice'
  return {
    key, type, title: `Title of ${key}`, minutes: 10, difficulty: null, skills: ['dsa.complexity_analysis'], tab, stages: ['LEARN'],
    observation_kind: 'STUDY_SESSION', time_limit_seconds: null, progress: null, ...extra,
  }
}

export const LESSON: ContentDetail = {
  ...summary('dsa.complexity.lesson', 'lesson', { title: 'Time and space complexity' }),
  body: {
    summary: 'Big-O describes how cost grows.',
    what: 'It estimates growth. <script>alert(1)</script> stays text.',
    why: 'Inputs are large.', when: 'Always.', how: '- one loop: `O(n)`\n- nested: **O(n²)**',
    mental_model: 'Double the input.', tradeoffs: 'Memory for time.', mistakes: ['`x in list` is O(n)'], interview: 'State it.',
    explain_it: ['Say what n is.'],
    example: { language: 'python', code: 'for x in a:\n    pass', explanation: 'One pass.' },
  },
  rubric: [], pass_points: null, problems: [], topic: { key: 'dsa.method', title: 'Problem-solving method', track: 'dsa' },
}

export const CHECK: ContentDetail = {
  ...summary('dsa.complexity.check', 'concept_check', { title: 'Concept check: complexity', observation_kind: 'RECALL_QUIZ' }),
  body: {
    intro: 'Closed book.',
    questions: [
      { id: 'q1', kind: 'single', prompt: 'Halving loop?', options: ['O(n)', 'O(log n)'] },
      { id: 'q2', kind: 'multi', prompt: 'Amortised O(1)?', options: ['append', 'pop()', 'pop(0)'] },
      { id: 'q3', kind: 'short', prompt: 'n ≤ 10⁵ and O(n²)?', model_answer: 'Too slow; aim for O(n log n).' },
    ],
  },
  rubric: [], pass_points: 60, problems: [], topic: null,
}

export const EXERCISE: ContentDetail = {
  ...summary('dsa.complexity.exercise', 'coding_exercise', {
    title: 'Make it linear', observation_kind: 'CODE_EXERCISE', time_limit_seconds: 900,
  }),
  body: {
    prompt: 'Rewrite `count_pairs` in O(n).', examples: ['count_pairs([1, 5], 6) == 1'], hints: ['Count complements.', 'Use a Counter.'],
    solution: { language: 'python', code: 'def count_pairs(): ...' },
    follow_ups: [{ prompt: 'Return the pairs?', look_for: 'Output size can be O(n²).' }],
  },
  rubric: [{ key: 'correct', label: 'Correct result', points: 4 }, { key: 'linear', label: 'Single pass', points: 3 }],
  pass_points: 70, problems: [], topic: null,
}

function record(kind: string): AssessmentRecord {
  return {
    id: 99, kind, observed_at: '2026-10-05T10:00:00Z', observed_on: '2026-10-05', mode: 'PRACTICE', source_key: 'content:x',
    notes_used: false, reference_used: false, hints_used: 0, timed: false, time_limit_seconds: null, time_seconds: null,
    followup_points: null, communication_points: null, familiarity: null, study_minutes: null, skills: [], notes: null,
    revision_item_key: null, battery_item_key: null, supersedes_id: null, superseded_by_id: null, is_current: true,
  }
}

export const CHECK_RESULT: CompletionResult = {
  content_key: 'dsa.complexity.check', points: 67, passed: true, followup_points: null,
  questions: [
    { id: 'q1', kind: 'single', earned: 2, chosen: [1], answer: [1], explanation: 'Halving is logarithmic.', model_answer: null },
    { id: 'q2', kind: 'multi', earned: 0, chosen: [0], answer: [0, 1], explanation: 'pop() is O(1) too.', model_answer: null },
    { id: 'q3', kind: 'short', earned: 2, chosen: [], answer: [], explanation: 'Constraints set the target.', model_answer: 'Too slow' },
  ],
  observation: record('RECALL_QUIZ'),
  progress: { completions: 1, last_points: 67, best_points: 67, last_on: '2026-10-05', passed: true, milestones_done: [], defended: false },
}

export const STUDY_RESULT: CompletionResult = { ...CHECK_RESULT, points: null, passed: null, questions: [], observation: record('STUDY_SESSION') }

export function learning(extra: Partial<SkillLearning> = {}): SkillLearning {
  return {
    skill: {
      key: 'graph.traversal', name: 'Graphs: BFS and DFS', component: 'dsa', group: 'dsa.graphs', tier: 'T1', importance: 100,
      target_score: 80, required: true,
    },
    why_it_matters: {
      tier_label: 'CRITICAL', importance: 100, target_score: 80, rounds: ['DSA'], unlocks: ['graph.topological_sort'],
      topic: { key: 'dsa.graphs', title: 'Graph traversal', track: 'dsa' },
    },
    state: {
      score: 51, effective_score: 43, label: 'DEVELOPING', confidence: 'MEDIUM', assessed: true, gap_status: 'CRITICAL',
      gap_type: 'PATTERN_RECOGNITION', focus_stage: 'PATTERN_DRILL', focus_skill: 'graph.traversal', reason_codes: [],
    },
    tabs: {
      learn: [summary('dsa.graph.lesson', 'lesson')],
      practice: [summary('dsa.graph.exercise', 'coding_exercise', { time_limit_seconds: 900 })],
      test: [summary('dsa.graph.check', 'concept_check')],
      revision: [summary('dsa.graph.cards', 'revision_card')],
    },
    practice: {
      case: 'DIRECT',
      direct: [{ id: 27, key: 'LEETCODE:number-of-islands', title: 'Number of Islands', difficulty: 'MEDIUM', expected_minutes: null,
        url: 'https://leetcode.com/problems/number-of-islands/', practice_state: 'solved_with_hint' }],
      related: [], fallback_skill: null, fallback_name: null, fallback_relation: null,
    },
    related_skills: [{ key: 'graph.grid_multisource', name: 'Grid BFS', relation: 'SAME_TOPIC' }],
    next_action: {
      kind: 'START_SESSION', stage: 'PATTERN_DRILL', reason: 'GAP_FOCUS', session_id: null, minutes: 18,
      steps: [{ position: 1, kind: 'CONTENT', title: 'Concept check', minutes: 8, content_key: 'dsa.graph.check', content_type: 'concept_check', problem_id: null },
        { position: 2, kind: 'PROBLEM', title: 'Number of Islands', minutes: 30, content_key: null, content_type: null, problem_id: 27 }],
      fallback_skill: null,
    },
    coverage_state: 'FULL',
    ...extra,
  }
}

export const CONCEPT_ONLY = learning({
  skill: { ...learning().skill, key: 'dsa.complexity_analysis', name: 'Complexity analysis' },
  practice: {
    case: 'CONCEPT', direct: [],
    related: [{ problem: { id: 1, key: 'LEETCODE:two-sum', title: 'Two Sum', difficulty: 'EASY', expected_minutes: null, url: null,
      practice_state: 'not_started' }, via_skill: 'hashing.lookup_frequency', via_name: 'Hashing', relation: 'USES_THIS' }],
    fallback_skill: null, fallback_name: null, fallback_relation: null,
  },
})

export const UNCOVERED = learning({
  tabs: { learn: [], practice: [], test: [], revision: [] },
  practice: { case: 'UNCOVERED', direct: [], related: [], fallback_skill: 'recursion.fundamentals', fallback_name: 'Recursion', fallback_relation: 'FOUNDATION' },
  next_action: { kind: 'NONE', stage: 'LEARN', reason: 'NO_CONTENT', session_id: null, minutes: null, steps: [], fallback_skill: null },
  coverage_state: 'CONTENT_GAP',
})

export const SESSION: LearningSession = {
  id: 5, skill: 'dsa.complexity_analysis', skill_name: 'Complexity analysis', stage: 'LEARN', status: 'ACTIVE', outcome: null,
  plan_item_id: null, budget_minutes: null, minutes: 31, started_at: '2026-10-05T10:00:00Z', completed_at: null, next_position: 1,
  steps: [
    { position: 1, kind: 'CONTENT', title: 'Time and space complexity', minutes: 20, status: 'PENDING', content_key: 'dsa.complexity.lesson',
      content_type: 'lesson', problem: null, observation_type: null, observation_id: null, points: null, passed: null, reflection: null },
    { position: 2, kind: 'CONTENT', title: 'Concept check', minutes: 8, status: 'PENDING', content_key: 'dsa.complexity.check',
      content_type: 'concept_check', problem: null, observation_type: null, observation_id: null, points: null, passed: null, reflection: null },
    { position: 3, kind: 'REFLECTION', title: 'Reflection', minutes: 3, status: 'PENDING', content_key: null, content_type: null,
      problem: null, observation_type: null, observation_id: null, points: null, passed: null, reflection: null },
  ],
  before: { score: null, level: null },
  after: { score: null, level: null },
}

export const TRACK: LearningTrackDetail = {
  key: 'dsa', title: 'Data structures & algorithms', summary: 'Patterns first.', components: ['dsa'], content_count: 3, done_count: 1,
  topics: [{
    key: 'dsa.method', title: 'Problem-solving method', summary: 'Clarify, brute force, complexity.',
    skills: [{ key: 'dsa.complexity_analysis', name: 'Complexity analysis', tier: 'T1', required: true, score: null, target_score: 80,
      label: 'UNASSESSED', status: 'UNASSESSED', content_count: 3, done_count: 1, coverage_state: 'PARTIAL' }],
  }],
  content: { 'dsa.method': [summary('dsa.complexity.lesson', 'lesson'), summary('dsa.complexity.check', 'concept_check')] },
}

export { SKILL_DETAIL }
