/** Response envelopes from the backend (docs/engineering/API_SPEC.md §1). */
export interface Meta {
  as_of_date?: string
  ruleset_version?: string
  seed_version?: string
  run_id?: number
  count?: number
}

export interface Envelope<T> {
  data: T
  meta: Meta
  /** Present on observation writes: consequences of the synchronous mentor run (D-056). */
  effects?: Effects
}

export interface SkillSnapshot {
  score: number | null
  effective: number | null
  level: number | null
  confidence: string
}

export interface SkillDelta {
  skill_key: string
  before: SkillSnapshot | null
  after: SkillSnapshot
}

export interface GapDelta {
  skill_key: string
  before: { priority: number; status: string } | null
  after: { priority: number; status: string }
}

export interface Effects {
  run_id: number
  skill_deltas: SkillDelta[]
  gap_deltas?: GapDelta[]
  revision_changes?: { item_key: string; change: string; state?: string; due_date: string | null }[]
  readiness_change?: { before: string | null; after: string; blockers_added: string[]; blockers_removed: string[] } | null
}

export interface ErrorBody {
  code: string
  message: string
  details: Record<string, unknown>
}

export interface ErrorEnvelope {
  error: ErrorBody
}

export interface HealthData {
  db: string
  ruleset_version: string
  seed_version: string | null
}

/* ---- Catalog (read-only, static seed data) ---- */
export interface CatalogSummary {
  seed_version: string
  catalog_fingerprint: string
  loaded_at: string
  versions: Record<string, string>
  files: { role: string; fingerprint: string }[]
  counts: Record<string, number>
}

export interface SkillRef {
  key: string
  name: string
  min_score: number | null
  depth: number | null
}

export interface SkillDetail {
  key: string
  name: string
  group: string
  component: string
  is_pattern: boolean
  tier: string | null
  importance: number | null
  target_score: number | null
  floor_score: number | null
  required: boolean | null
  prerequisites: SkillRef[]
  dependents: SkillRef[]
  milestone: { key: string; name: string; track: string } | null
  problem_count: number
}

export interface ComponentNode {
  component: string
  groups: { key: string; name: string; component: string; skills: string[] }[]
}

export interface RoleProfile {
  profile_key: string
  name: string
  seniority: string
  config: {
    components: { key: string; name: string; weight: number; gate: number; stretch: number; track: string }[]
    [key: string]: unknown
  }
  tier_counts: Record<string, number>
  required_skill_count: number
  critical_skills: string[]
}

export interface Roadmap {
  tracks: { track: string; milestones: { key: string; name: string; position: number; skills: string[] }[] }[]
  baseline_items: { key: string; name: string; minutes: number }[]
  baseline_total_minutes: number
}

/* ---- Activity capture (raw observations; no scores) ---- */
export type Outcome = 'PASS' | 'PARTIAL' | 'FAIL'

export interface ProblemSummary {
  id: number
  key: string
  platform: string
  platform_key: string
  title: string
  url: string | null
  difficulty: 'EASY' | 'MEDIUM' | 'HARD'
  expected_minutes: number | null
  is_canonical: boolean
  source: 'CATALOG' | 'PERSONAL'
  skills: { skill: string; mapping_weight_bp: number; primary: boolean }[]
  attempt_count: number
  last_attempt: { id: number; attempted_at: string; outcome: Outcome } | null
}

export interface ProblemAttempt {
  id: number
  problem: { id: number; key: string; title: string; difficulty: string; source: string }
  attempted_at: string
  attempted_on: string
  mode: string
  outcome: Outcome
  seen_elsewhere: boolean
  hints_used: number
  solution_viewed: boolean
  pattern_identified: boolean | null
  timed: boolean
  time_limit_seconds: number | null
  time_seconds: number | null
  explanation_score: number | null
  complexity_correct: boolean | null
  followup_solved: boolean | null
  execution_rubric: Record<string, number> | null
  mistakes: string[]
  self_rating_before: number | null
  self_rating_after: number | null
  notes: string | null
  supersedes_id: number | null
  superseded_by_id: number | null
  is_current: boolean
  created_at: string
}

/** Body of POST /problem-attempts (Spec v2 field names). */
export interface ProblemAttemptInput {
  problem_id: number
  outcome: Outcome
  attempted_at?: string
  hints_used: number
  solution_viewed: boolean
  seen_elsewhere: boolean
  pattern_identified?: boolean
  timed: boolean
  time_limit_seconds?: number
  time_seconds?: number
  explanation_score?: number
  complexity_correct?: boolean
  followup_solved?: boolean
  mistakes: string[]
  self_rating_before?: number
  self_rating_after?: number
  notes?: string
  client_request_id: string
}

/* ---- Skill state (derived; computed by the backend engines only) ---- */
export interface SkillState {
  score: number | null
  effective_score: number | null
  level: number | null
  confidence: 'NONE' | 'LOW' | 'MEDIUM' | 'HIGH'
  label: string
  peak_score: number | null
  evidence_count: number
  distinct_sources: number
  last_practiced_on: string | null
  last_observed_on: string | null
  reality_capped: boolean
  declared_unknown: boolean
  assessed: boolean
}

export interface GapSummary {
  status: string
  priority: number
  rank: number
  primary_gap_type: string | null
  focus_stage: string | null
  focus_skill: string | null
  reason_codes: string[]
  blocked_by: { skill: string; score: number | null; min_score: number }[]
  parked_reason: string | null
}

export interface SkillWithState {
  key: string
  name: string
  group: string
  component: string
  tier: string | null
  importance: number | null
  target_score: number | null
  floor_score: number | null
  required: boolean | null
  state: SkillState
  gap: GapSummary | null
}

export interface EvidenceRow {
  source_type: 'ATTEMPT' | 'ASSESSMENT' | 'MOCK_ROUND'
  source_id: number
  rule: string
  kind: string | null
  level: number
  outcome_points: number | null
  is_scoring: boolean
  observed_on: string
  observed_at: string
  difficulty_bp: number
  mapping_bp: number
  source_key: string
  timed: boolean
  within_limit: boolean | null
  is_unseen: boolean | null
  is_weakness: boolean
  familiarity: string | null
  considered: boolean
  qualifying: boolean
}

export interface SkillStateDetail extends SkillWithState {
  prerequisites: { skill: string; min_score: number; effective_score: number | null; satisfied: boolean }[]
  dependents: string[]
  milestone: { key: string; name: string; track: string } | null
  revision_items: { item_key: string; item_type: string; state: string; due_date: string | null; interval_index: number; lapses: number }[]
  focus: { stage: string; template_key: string | null; minutes: number | null; pass_rule: string | null; observation_kind: string | null } | null
  evidence: EvidenceRow[]
}

export interface RoadmapView {
  as_of_date: string
  tracks: {
    track: string
    current_milestone: string | null
    milestones: {
      key: string; name: string; position: number; content: string | null
      skills: { key: string; required: boolean; level: number | null; done: boolean }[]
      required_total: number; required_done: number
      extra_exit: { text: string; met: boolean }[]
      complete: boolean; current: boolean
    }[]
  }[]
  baseline: { done: number; total: number; next_item: string | null; calibration_mode: boolean }
}

export interface BatteryItem {
  key: string
  position: number
  name: string
  minutes: number
  observation_kind: string
  covers: string[]
  complete: boolean
}

export type CalibrationPhase = 'NOT_STARTED' | 'IN_PROGRESS' | 'ENOUGH_MEASURED' | 'COMPLETE'

export interface Baseline {
  items: BatteryItem[]
  battery_complete: boolean
  battery_done: number
  battery_total: number
  next_item: string | null
  required: number
  assessed_required: number
  assessed_pct: number
  calibration_mode: boolean
  phase: CalibrationPhase
  personalization_threshold_pct: number
  minutes_total: number
  minutes_done: number
  minutes_remaining: number
  typical_daily_minutes: number | null
  estimated_days: number | null
}

export type Familiarity = 'NONE' | 'SOME' | 'SOLID'

/** Body of POST /assessments. */
export interface AssessmentInput {
  kind: string
  source_key: string
  mode?: string
  notes_used: boolean
  reference_used: boolean
  hints_used: number
  timed: boolean
  time_limit_seconds?: number
  time_seconds?: number
  followup_points?: number
  communication_points?: number
  skills: { skill: string; outcome_points: number }[]
  battery_item_key?: string
  revision_item_key?: string
  notes?: string
  client_request_id: string
}

/* ---- Settings and goals ---- */
export interface Settings {
  timezone: string
  display_name: string
}

export interface GoalVersion {
  id: number
  profile_key: string
  target_date: string | null
  weekday_budgets: number[]
  weekly_minutes: number
  valid_from: string
  valid_to: string | null
  is_active: boolean
  created_at: string
}

export interface ActiveGoal extends GoalVersion {
  phase: 'BUILD' | 'CONSOLIDATE' | 'SHARPEN'
  weeks_left: string | null
}

/* ---- Revision ---- */
export interface RevisionItem {
  item_key: string
  item_type: string
  skill: string
  skill_name: string
  tier: string | null
  importance: number | null
  parked: boolean
  state: 'ACTIVE' | 'SUSPENDED' | 'GRADUATED'
  suspend_reason: string | null
  interval_index: number
  due_date: string | null
  days_overdue: number
  lapses: number
  needs_reinforcement: boolean
  minutes: number
  bucket: 'overdue' | 'due' | 'upcoming' | 'maintenance' | 'suspended' | 'graduated'
  review_kind: string
  subject_ref: string
  last_reviewed_on: string | null
}

export interface RevisionList {
  backlog_minutes: number
  cap_minutes: number
  triage_threshold_minutes: number
  counts: Record<string, number>
  items: RevisionItem[]
}

/* ---- Today and plan ---- */
export interface PlanItem {
  id: number
  position: number
  candidate_type: string
  candidate_key: string
  skill: string | null
  stage: string | null
  minutes: number
  candidate_score: number
  template: { key: string; observation: Record<string, unknown>; pass_rule: string; output_level: number; next_on_pass: string | null } | null
  problems: { id: number; key: string; title: string; difficulty: string; url: string | null }[]
  revision_item_key: string | null
  battery_item_key: string | null
  round_type: string | null
  reason_codes: string[]
  explanation: { current?: number | null; effective?: number | null; target?: number | null; priority?: number | null; evidence?: string; expected_outcome?: string }

  status: 'PENDING' | 'DONE' | 'SKIPPED' | 'DEFERRED' | 'DISCARDED'
  skip_reason: string | null
  observation_type: string | null
  observation_id: number | null
  no_evidence: boolean
  carried_over_from_id: number | null
  started_at: string | null
  completed_at: string | null
}

export interface Plan {
  id: number
  plan_date: string
  run_id: number
  ruleset_version: string
  budget_minutes: number
  allocated_minutes: number
  unallocated_minutes: number
  done_minutes: number
  phase: string
  calibration_mode: boolean
  regenerated_count: number
  items: PlanItem[]
  stop_list: { skill: string; code: string; instruction: string; minutes_7d: number }[]
  dropped: { key: string; reason: string; detail: string | null }[]
  message: { rule: string; text: string; payload: Record<string, unknown> }
}

export interface Today {
  plan_date: string
  phase: string
  weeks_left: string | null
  goal_exists: boolean
  calibration: { active: boolean; assessed: number; required: number; assessed_pct: number; battery_done: number; battery_total: number; next_item: string | null }
  readiness: {
    state: string
    weighted_score: number
    limiting_component: string | null
    blockers: { gate: string; message: string; component?: string | null; skill?: string | null; actual?: unknown; required?: unknown }[]
  }
  top_gaps: { skill_key: string; status: string; priority: number; primary_gap_type: string | null; focus_stage: string | null; reason_codes: string[] }[]
  revisions: { due: number; overdue: number; backlog_minutes: number; cap_minutes: number }
  plan: Plan
}

/* ---- Readiness (gate-based; weighted score is display-only) ---- */
export interface ReadinessCondition {
  gate: string
  subject: string
  kind: string
  actual: unknown
  required: unknown
  deficit: number
  message: string
  skills: string[]
}

export interface Readiness {
  as_of_date: string
  run_id: number
  ruleset_version: string
  state: 'NOT_MEASURED' | 'FOUNDATION' | 'DEVELOPING' | 'INTERVIEW_READY' | 'STRONG'
  simulation_eligible: boolean
  lapsed: boolean
  weighted_score: number
  limiting_component: string | null
  components: { key: string; name: string; score: number; gate: number; stretch: number; weight: number; assessed_pct: number; medium_conf_pct: number; passes_gate: boolean }[]
  gates: { gate: string; passed: boolean; failing: number }[]
  blockers: ReadinessCondition[]
  all_failing: ReadinessCondition[]
}

export interface ReadinessPoint {
  date: string
  state: string
  weighted_score: number
  limiting_component: string | null
  components: Record<string, number>
  blockers: number
}

export interface AssessmentRecord {
  id: number
  kind: string
  observed_at: string
  observed_on: string
  mode: string
  source_key: string
  notes_used: boolean
  reference_used: boolean
  hints_used: number
  timed: boolean
  time_limit_seconds: number | null
  time_seconds: number | null
  followup_points: number | null
  communication_points: number | null
  familiarity: string | null
  study_minutes: number | null
  skills: { skill: string; outcome_points: number | null; mapping_weight_bp: number; is_pattern_target: boolean }[]
  notes: string | null
  revision_item_key: string | null
  battery_item_key: string | null
  supersedes_id: number | null
  superseded_by_id: number | null
  is_current: boolean
}

/* ---- Mocks and content ---- */
export type RoundType = 'DSA' | 'CS' | 'LLD' | 'SYSTEM_DESIGN' | 'BEHAVIORAL' | 'PROJECT_DEEP_DIVE'

export interface MockRoundInput {
  round_type: RoundType
  duration_minutes: number
  round_score: number
  skills: { skill: string; outcome_points: number; is_weakness: boolean }[]
}

export interface MockRecord {
  id: number
  occurred_on: string
  source: string
  is_final_simulation: boolean
  rounds: (MockRoundInput & { id: number; position: number })[]
  is_current: boolean
}

export interface MockSummary {
  as_of_date: string
  by_type: { round_type: string; rounds_60d: number; required_60d: number; non_self_60d: number; latest: { date: string; score: number } | null; trend: { date: string; score: number }[]; g6_failing: string[] }[]
  g6_passed: boolean
  repeated_weaknesses: [string, number][]
  final_simulations: { mock_id: number; date: string; source: string; valid: boolean; passed: boolean; failure: string | null }[]
  g9_passed: boolean
  g9_failing: string[]
  simulation_eligible: boolean
}

export interface Story { id: number; title: string; competencies: string[]; archived: boolean }
export interface ProjectRecord { id: number; project_key: string; name: string; summary: string }
export interface PromptRecord { id: number; prompt_key: string; skill: string; kind: string; prompt_text: string; source_key: string }

/* ---- Weekly review ---- */
export interface WeeklyReview {
  id: number
  week_start: string
  metrics: {
    week_start: string; week_end: string; active_days: number; planned_minutes: number; completed_minutes: number
    plan_completion_pct: number | null; revision_completion_pct: number | null
    minutes_by_track: Record<string, { minutes: number; weekly_target: number }>
    top_gaps: { skill_key: string; status: string; priority: number; primary_gap_type: string | null }[]
    gap_changes: { skill_key: string; before: number | null; after: number | null; delta: number }[]
    strongest_improvement: { skill_key: string; before: number; after: number; delta: number } | null
    biggest_regression: { skill_key: string; before: number; after: number; delta: number } | null
    readiness: { start: { state: string; weighted_score: number }; end: { state: string; weighted_score: number }; new_blockers: string[]; cleared_blockers: string[] }
    mocks: { date: string; round_type: string; score: number }[]
    backlog_minutes: number
  }
  next_focus: { top_gaps: { skill_key: string; status: string; priority: number }[]; tracks_below_floor: string[]; stop_list: string[] }
  reflection: Record<string, string> | null
  reflected_at: string | null
}

/* ---- Week-to-date context for Today (GET /today/week) ---- */
export interface WeekContext {
  plan_date: string
  week_start: string
  week_end: string
  preparation_day: number | null
  target_minutes: number | null
  practice_minutes: number
  active_days: number
  minutes_by_track: { track: string; minutes: number; weekly_target: number }[]
  revision: { planned: number; done: number; completion_pct: number | null }
}

/** Per-skill gap detail (GET /gaps/{skill}); `metrics` are the numbers the explanation may quote. */
export interface GapDetail {
  skill_key: string
  name: string
  component: string
  current_score: number | null
  effective_score: number | null
  target_score: number
  floor_score: number
  status: string
  priority: number
  primary_gap_type: string | null
  reason_codes: string[]
  blocked_by: { skill: string; score: number | null; min_score: number }[]
  parked_reason: string | null
  recommended_focus: { stage: string; focus_skill: string }
  metrics: {
    peak_score: number | null
    n_fail_last5: number
    component_gate: number
    component_score: number
    depth_mean_last3: number | null
    overconfident_rows: number
    pattern_misses_last4: number
    speed_median_ratio_bp: number | null
    communication_mean_last3: number | null
    days_since_last_practice: number | null
  }
}

/* ---- Starting profile, personal roadmap and current state (D-080) ---- */
export type SelfReportClaim = 'strengths' | 'weaknesses' | 'never_studied' | 'recently_studied'

export interface RoleOption {
  profile_key: string
  name: string
  seniority: string
}

export interface StartingProfile {
  display_name: string
  timezone: string
  onboarding: { completed: boolean; completed_at: string | null }
  experience: { years: number | null; current_role: string | null; previous_role: string | null }
  technologies: string[]
  company_profile: string | null
  self_report: Record<SelfReportClaim, string[]>
  target: {
    role: RoleOption
    target_date: string | null
    weekday_budgets: number[]
    weekly_minutes: number
    phase: string
    weeks_left: string | null
  } | null
  available_roles: RoleOption[]
}

export interface OnboardingBody {
  display_name?: string
  experience?: { years?: number | null; current_role?: string | null; previous_role?: string | null }
  technologies?: string[]
  company_profile?: string
  self_report?: Partial<Record<SelfReportClaim, string[]>>
  goal: { target_date?: string | null; weekday_budgets?: number[]; profile_key?: string }
}

export type RoadmapBucket = 'build' | 'consolidate' | 'sharpen' | 'maintain' | 'parked' | 'unmeasured'

export interface RoadmapItem {
  skill_key: string
  name: string
  component: string
  bucket: RoadmapBucket
  health: 'strong' | 'developing' | 'critical' | 'unknown' | 'parked'
  score: number | null
  target: number
  status: string
  priority: number
  confidence: string
  declared_unknown: boolean
  primary_gap_type: string | null
  focus_stage: string | null
  focus_skill: string | null
  focus_skill_name: string | null
  reason_codes: string[]
  importance: number
  prerequisites: { skill: string; name: string; score: number | null; min_score: number }[]
  next_step_minutes: number | null
}

export interface FocusChange {
  skill_key: string
  name: string
  priority_before: number | null
  priority_after: number | null
  reason_codes: string[]
}

export interface PersonalRoadmap {
  as_of_date: string
  calibration_phase: CalibrationPhase
  available: boolean
  based_on: {
    role: RoleOption | null
    target_date: string | null
    weeks_left: string | null
    phase: string
    measured_skills: number
    required_skills: number
    blocked_skills: number
    overdue_reviews: number
  }
  focus_now: RoadmapItem[]
  sections: Record<RoadmapBucket | 'later', { count: number; items: RoadmapItem[] }>
  why: {
    skill_key: string
    name: string
    component: string
    score: number | null
    target: number
    importance: number
    priority: number
    reason_codes: string[]
    metrics: GapDetail['metrics']
    prerequisites: { skill: string; name: string; score: number | null; min_score: number }[]
  }[]
  changes: { since: string; changed: boolean; entered: FocusChange[]; left: FocusChange[] }
}

export interface CurrentState {
  as_of_date: string
  calibration_phase: CalibrationPhase
  counts: Record<string, number>
  strong: { count: number; items: RoadmapItem[] }
  developing: { count: number; items: RoadmapItem[] }
  critical: { count: number; items: RoadmapItem[] }
  unknown: { count: number; items: RoadmapItem[] }
  self_reported: {
    group_key: string
    name: string
    component: string
    claims: ('STRONG' | 'WEAK' | 'NEVER_STUDIED' | 'RECENTLY_STUDIED')[]
    measured: number
    total: number
    skills: {
      skill_key: string
      name: string
      score: number | null
      target: number | null
      confidence: string
      status: string
      declared_unknown: boolean
    }[]
  }[]
}
