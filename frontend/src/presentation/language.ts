/** Human wording for backend vocabularies. Display only: values are never interpreted or recomputed here. */

export type SemanticState =
  | 'critical' | 'high' | 'medium' | 'low' | 'healthy' | 'ready' | 'due' | 'overdue' | 'blocked'
  | 'calibration' | 'completed' | 'parked'

export const STATE_LABEL: Record<SemanticState, string> = {
  critical: 'Critical',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
  healthy: 'Healthy',
  ready: 'Ready',
  due: 'Revision due',
  overdue: 'Overdue',
  blocked: 'Blocked',
  calibration: 'Calibrating',
  completed: 'Completed',
  parked: 'Parked',
}

/** Gap status from the gap engine -> the semantic state shown to the user. */
export function stateFromGapStatus(status: string): SemanticState {
  switch (status) {
    case 'CRITICAL': return 'critical'
    case 'HIGH': return 'high'
    case 'MEDIUM': return 'medium'
    case 'LOW': return 'low'
    case 'NONE': return 'healthy'
    case 'BLOCKED': return 'blocked'
    case 'PARKED': return 'parked'
    default: return 'calibration' // UNASSESSED
  }
}

export const GAP_STATUS_LABEL: Record<string, string> = {
  CRITICAL: 'Critical', HIGH: 'High', MEDIUM: 'Medium', LOW: 'Low', NONE: 'On target',
  UNASSESSED: 'Not measured yet', BLOCKED: 'Blocked', PARKED: 'Parked',
}

export const ACTIONABLE_GAP_STATUSES = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] as const

export const PHASE_LABEL: Record<string, string> = {
  CALIBRATION: 'Calibration',
  BUILD: 'Building foundations',
  CONSOLIDATE: 'Consolidation',
  SHARPEN: 'Interview sharpening',
}

export const READINESS_LABEL: Record<string, string> = {
  NOT_MEASURED: 'Not measured yet',
  FOUNDATION: 'Foundation',
  DEVELOPING: 'Developing',
  INTERVIEW_READY: 'Interview ready',
  STRONG: 'Strong',
}

/** One calm sentence per readiness state ("You're ready to simulate" rather than "Readiness state: SHARPEN"). */
export const READINESS_SUMMARY: Record<string, string> = {
  NOT_MEASURED: "We're calibrating your baseline.",
  FOUNDATION: 'The basics are forming. Keep building.',
  DEVELOPING: 'Solid progress. A few areas still hold you back.',
  INTERVIEW_READY: "You're ready to simulate real interviews.",
  STRONG: 'Strong across the board. Keep it sharp.',
}

export const COMPONENT_LABEL: Record<string, string> = {
  dsa: 'DSA',
  coding: 'Coding',
  cs: 'CS Fundamentals',
  lld: 'LLD / OOD',
  system_design: 'System Design',
  behavioral: 'Behavioral',
  project: 'Projects',
}

export const TRACK_LABEL: Record<string, string> = {
  dsa_coding: 'DSA & coding',
  cs: 'CS fundamentals',
  lld: 'LLD / OOD',
  system_design: 'System design',
  behavioral_project: 'Behavioral & projects',
  mock: 'Mocks',
}

export const STAGE_LABEL: Record<string, string> = {
  DIAGNOSE: 'Diagnostic',
  LEARN: 'Learn',
  RECALL: 'Recall quiz',
  GUIDED: 'Guided practice',
  INDEPENDENT: 'Independent practice',
  TIMED: 'Timed practice',
  EXPLAIN: 'Explain it',
  TRANSFER: 'New-variant practice',
  SIMULATE: 'Interview simulation',
  PATTERN_DRILL: 'Pattern drill',
  REINFORCE: 'Reinforcement',
  THINK_ALOUD: 'Think-aloud practice',
  PREREQUISITE: 'Fix the prerequisite',
}

export const GAP_TYPE_LABEL: Record<string, string> = {
  UNASSESSED: 'Not measured yet',
  PREREQUISITE: 'Missing prerequisite',
  KNOWLEDGE: 'Knowledge',
  RETENTION: 'Retention',
  PATTERN_RECOGNITION: 'Pattern recognition',
  PRACTICE: 'Practice',
  CONFIDENCE: 'Overconfidence',
  SPEED: 'Speed',
  DEPTH: 'Depth',
  COMMUNICATION: 'Communication',
  INTERVIEW_EXECUTION: 'Interview execution',
  EXPERIENCE: 'Real-world experience',
  LEVEL_UP: 'Next level',
}

export const LEVEL_LABEL: Record<string, string> = {
  UNASSESSED: 'Not measured', WEAK: 'Weak', DEVELOPING: 'Developing', WORKING: 'Working',
  STRONG: 'Strong', INTERVIEW_GRADE: 'Interview-grade',
}

export const CONFIDENCE_LABEL: Record<string, string> = {
  NONE: 'None yet', LOW: 'Low', MEDIUM: 'Medium', HIGH: 'High',
}

export const SOURCE_LABEL: Record<string, string> = {
  ATTEMPT: 'Practice attempt', ASSESSMENT: 'Assessment', MOCK_ROUND: 'Mock interview',
}

export const OBSERVATION_LABEL: Record<string, string> = {
  ATTEMPT: 'a problem attempt', RECALL_QUIZ: 'a recall quiz', CONCEPT_EXPLAIN: 'a concept explanation',
  PATTERN_DRILL: 'a pattern drill', CODE_EXERCISE: 'a coding exercise', ESTIMATION_DRILL: 'an estimation drill',
  SD_DESIGN: 'a system design', LLD_DESIGN: 'a low-level design', MACHINE_CODING: 'a machine-coding session',
  STORY_REHEARSAL: 'a story rehearsal', PROJECT_WALKTHROUGH: 'a project walkthrough', APPLIED_TASK: 'an applied task',
  STUDY_SESSION: 'a study session', SELF_ASSESSMENT: 'a self-assessment',
}

/** The nav groups of the Prepare section: category -> backend components it covers. */
export const PREPARE_CATEGORIES = [
  { slug: 'dsa', label: 'DSA', icon: 'code', primary: 'dsa', components: ['dsa', 'coding'] },
  { slug: 'cs', label: 'CS Fundamentals', icon: 'database', primary: 'cs', components: ['cs'] },
  { slug: 'system-design', label: 'System Design', icon: 'layers', primary: 'system_design', components: ['system_design'] },
  { slug: 'lld', label: 'LLD / OOD', icon: 'box', primary: 'lld', components: ['lld'] },
  { slug: 'behavioral', label: 'Behavioral', icon: 'message', primary: 'behavioral', components: ['behavioral', 'project'] },
] as const

export type PrepareCategory = (typeof PREPARE_CATEGORIES)[number]

/** Learning tracks (seed/learning/curriculum.yaml) per Prepare page. The five scored areas keep their pages;
 * Python, practical engineering and projects are curriculum pages (their skills score inside DSA/coding and project). */
export const TRACK_OF_SLUG: Record<string, string> = {
  dsa: 'dsa', cs: 'cs', 'system-design': 'system_design', lld: 'lld', behavioral: 'behavioral',
  python: 'python', engineering: 'engineering', projects: 'projects', communication: 'communication',
}
export const CURRICULUM_PAGES = [
  { slug: 'python', label: 'Python', icon: 'code', track: 'python' },
  { slug: 'engineering', label: 'Practical engineering', icon: 'zap', track: 'engineering' },
  { slug: 'projects', label: 'Projects', icon: 'flag', track: 'projects' },
  { slug: 'communication', label: 'Communication', icon: 'message', track: 'communication' },
] as const
/** Prepare navigation order: the scored areas with the curriculum pages where a learner looks for them. */
export const PREPARE_NAV = [
  { slug: 'dsa', label: 'DSA', icon: 'code', route: 'dsa' },
  { slug: 'python', label: 'Python', icon: 'code', route: 'curriculum' },
  { slug: 'cs', label: 'CS Fundamentals', icon: 'database', route: 'track' },
  { slug: 'system-design', label: 'System Design', icon: 'layers', route: 'track' },
  { slug: 'lld', label: 'LLD / OOD', icon: 'box', route: 'track' },
  { slug: 'engineering', label: 'Practical engineering', icon: 'zap', route: 'curriculum' },
  { slug: 'projects', label: 'Projects', icon: 'flag', route: 'curriculum' },
  { slug: 'behavioral', label: 'Behavioral', icon: 'message', route: 'track' },
  { slug: 'communication', label: 'Communication', icon: 'mocks', route: 'curriculum' },
] as const

export function prepareRoute(slug: string): { name: string; params?: Record<string, string> } {
  const item = PREPARE_NAV.find((p) => p.slug === slug)
  if (!item) return { name: 'prepare' }
  return item.route === 'dsa' ? { name: 'dsa' } : { name: item.route, params: { slug } }
}

export function categoryForComponent(component: string): PrepareCategory | undefined {
  return PREPARE_CATEGORIES.find((c) => (c.components as readonly string[]).includes(component))
}

export const ROUND_LABEL: Record<string, string> = {
  DSA: 'DSA', CS: 'CS fundamentals', LLD: 'LLD / OOD', SYSTEM_DESIGN: 'System design', BEHAVIORAL: 'Behavioral',
  PROJECT_DEEP_DIVE: 'Project deep dive',
}

export const REVIEW_KIND_LABEL: Record<string, string> = {
  PROBLEM: 'Re-solve', PATTERN: 'Pattern drill', CS: 'Recall', PROJECT: 'Project walkthrough', STORY: 'Story rehearsal',
  MOCKW: 'Mock weakness', SD: 'Design recall', LLD: 'Design recall',
}

/** Personal roadmap sections (D-080). The engine decides which skill is in which one; this words them. */
export const BUCKET_LABEL: Record<string, string> = {
  build: 'Build', consolidate: 'Consolidate', sharpen: 'Sharpen', maintain: 'Maintain', parked: 'Parked',
  unmeasured: 'Not measured yet',
}
export const BUCKET_HINT: Record<string, string> = {
  build: 'The fundamentals are missing: learn and practise with support.',
  consolidate: 'Partly there: make it consistent without help.',
  sharpen: 'Understood: now timed practice and interview delivery.',
  maintain: 'At or above your target: only periodic revision.',
  parked: 'Not worth your time yet for this target and date.',
  unmeasured: 'No evidence yet.',
}
export const BUCKET_ICON: Record<string, string> = {
  build: 'layers', consolidate: 'refresh', sharpen: 'target', maintain: 'check-circle', parked: 'pause', unmeasured: 'help',
}

export const CLAIM_LABEL: Record<string, string> = {
  STRONG: 'Strong', WEAK: 'Weak', NEVER_STUDIED: 'Never studied', RECENTLY_STUDIED: 'Recently studied',
}

/** Wording for the self-report questions: server key -> label. */
export const SELF_REPORT_CLAIMS = [
  { key: 'strengths', label: 'Strong', hint: 'I would be comfortable being tested on this' },
  { key: 'weaknesses', label: 'Weak', hint: 'I struggle with this' },
  { key: 'never_studied', label: 'Never studied', hint: 'This is new to me' },
  { key: 'recently_studied', label: 'Recently studied', hint: 'I worked on this in the last few months' },
] as const

export const TECHNOLOGY_SUGGESTIONS = [
  'Python', 'JavaScript', 'TypeScript', 'PHP', 'Java', 'C++', 'Vue', 'React', 'Django', 'FastAPI', 'Node.js', 'SQL',
  'MySQL', 'PostgreSQL', 'Redis', 'Docker', 'AWS',
] as const

export const CALIBRATION_LABEL: Record<string, string> = {
  NOT_STARTED: 'Not started', IN_PROGRESS: 'In progress', ENOUGH_MEASURED: 'Enough measured', COMPLETE: 'Complete',
}
