import type { ContentType, CoverageState, LearningTab, PracticeCase, ProblemPracticeState } from '../api/types'
import type { SemanticState } from './language'

/** Wording for the learning layer (D-083). Words what the server sent; never decides anything. */

export const CONTENT_TYPE_LABEL: Record<ContentType, string> = {
  lesson: 'Lesson',
  concept: 'Concept',
  worked_example: 'Worked example',
  visual_explanation: 'Visual walkthrough',
  concept_check: 'Concept check',
  quiz: 'Quiz',
  coding_exercise: 'Coding exercise',
  guided_problem: 'Guided problem',
  timed_problem: 'Timed problem',
  debugging_exercise: 'Debugging scenario',
  sql_exercise: 'SQL exercise',
  design_exercise: 'Design exercise',
  architecture_case: 'Architecture case',
  project: 'Project',
  interview_question: 'Interview question',
  behavioral_question: 'Behavioral question',
  revision_card: 'Recall cards',
}

export const CONTENT_TYPE_ICON: Record<ContentType, string> = {
  lesson: 'book',
  concept: 'book',
  worked_example: 'list',
  visual_explanation: 'layers',
  concept_check: 'check-circle',
  quiz: 'check-circle',
  coding_exercise: 'code',
  guided_problem: 'code',
  timed_problem: 'clock',
  debugging_exercise: 'search',
  sql_exercise: 'database',
  design_exercise: 'box',
  architecture_case: 'layers',
  project: 'flag',
  interview_question: 'message',
  behavioral_question: 'message',
  revision_card: 'refresh',
}

export const TAB_LABEL: Record<LearningTab, string> = {
  learn: 'Learn',
  practice: 'Practice',
  test: 'Test',
  revision: 'Revise',
}

export const TAB_EMPTY: Record<LearningTab, string> = {
  learn: 'No lesson for this skill yet.',
  practice: 'No practice item for this skill yet.',
  test: 'No concept check for this skill yet.',
  revision: 'No recall cards for this skill yet.',
}

/** What a completion records, said plainly (EVIDENCE_MODEL levels without the jargon). */
export const RECORDS_LABEL: Record<string, string> = {
  STUDY_SESSION: 'counts as study time (it shows exposure, not ability)',
  RECALL_QUIZ: 'counts as recall when done closed-book',
  CODE_EXERCISE: 'counts as practice; timed and explained work counts more',
  CONCEPT_EXPLAIN: 'counts as practice; timed and explained work counts more',
  LLD_DESIGN: 'counts as design practice',
  MACHINE_CODING: 'counts as machine-coding practice',
  SD_DESIGN: 'counts as design practice',
  ESTIMATION_DRILL: 'counts as estimation practice',
  STORY_REHEARSAL: 'counts as a rehearsed story',
  PROJECT_WALKTHROUGH: 'counts as a project walkthrough',
  APPLIED_TASK: 'counts as applied work',
  ATTEMPT: 'records a problem attempt',
}

export const PRACTICE_STATE_LABEL: Record<ProblemPracticeState, string> = {
  not_started: 'Not started',
  attempted: 'Attempted',
  failed: 'Not solved yet',
  solved_after_solution: 'Solved after the solution',
  solved_with_hint: 'Solved with a hint',
  independent_solve: 'Solved independently',
  timed_solve: 'Solved under time',
  interview_grade: 'Interview grade',
}

export const PRACTICE_STATE_TONE: Record<ProblemPracticeState, SemanticState> = {
  not_started: 'low',
  attempted: 'medium',
  failed: 'high',
  solved_after_solution: 'medium',
  solved_with_hint: 'medium',
  independent_solve: 'healthy',
  timed_solve: 'healthy',
  interview_grade: 'ready',
}

export const PRACTICE_CASE_TEXT: Record<PracticeCase, string> = {
  DIRECT: 'Problems that practise this skill directly, easiest first.',
  RELATED:
    'No problem practises this skill on its own, so these related problems exercise it together with a neighbouring skill.',
  CONCEPT:
    'This is a concept skill: you prove it by explaining and reasoning, not by solving a coding problem. Use the checks and questions below.',
  UNCOVERED: 'There is no practice for this skill in the library yet.',
}

export const RELATION_TEXT: Record<string, string> = {
  USES_THIS: 'uses this skill',
  FOUNDATION: 'builds the foundation',
  SAME_GROUP: 'same family of skills',
  PREREQUISITE: 'Prerequisite',
  DEPENDENT: 'Builds on this',
  SAME_TOPIC: 'Same topic',
}

export const COVERAGE_LABEL: Record<CoverageState, string> = {
  FULL: 'Full path',
  PARTIAL: 'Partial path',
  UNMEASURED: 'Reading only',
  CONTENT_GAP: 'No content yet',
}

export const COVERAGE_TONE: Record<CoverageState, SemanticState> = {
  FULL: 'healthy',
  PARTIAL: 'medium',
  UNMEASURED: 'high',
  CONTENT_GAP: 'critical',
}

export const NEXT_REASON_TEXT: Record<string, string> = {
  GAP_FOCUS: 'The mentor picked this stage from your evidence.',
  UNASSESSED: 'Not measured yet: start with the lesson and a short check.',
  MAINTAIN: 'You are on target: a short recall keeps it fresh.',
  ACTIVE_SESSION: 'You have a session in progress.',
  NO_CONTENT: 'No learning content for this stage yet.',
  PREREQUISITE_FIRST: 'A prerequisite explains the weakness, so the mentor starts there.',
}

/** Lesson body sections in reading order. */
export const LESSON_SECTIONS: [string, string][] = [
  ['what', 'What it is'],
  ['why', 'Why it exists'],
  ['when', 'When to use it'],
  ['how', 'How it works'],
  ['mental_model', 'Mental model'],
  ['internals', 'Under the hood'],
  ['example', 'Example'],
  ['complexity', 'Complexity'],
  ['tradeoffs', 'Trade-offs'],
  ['edge_cases', 'Edge cases'],
  ['mistakes', 'Common mistakes'],
  ['misconceptions', 'Misconceptions'],
  ['interview', 'In the interview'],
  ['explain_it', 'Explain it in your own words'],
]

export const RATING_LABEL = ['Missed', 'Partly', 'Fully'] as const

export function contentTo(key: string): { name: string; params: { key: string } } {
  return { name: 'learn', params: { key } }
}

export function formatLimit(seconds: number | null): string | null {
  if (!seconds) return null
  const minutes = Math.round(seconds / 60)
  return `${minutes} min limit`
}
