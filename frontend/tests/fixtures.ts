import type {
  Baseline, CalibrationPhase, CurrentState, MockSummary, PersonalRoadmap, RoadmapItem, StartingProfile, PlanItem, Readiness, ReadinessPoint, RevisionItem, RevisionList, RoadmapView, SkillStateDetail,
  SkillWithState, Today, WeekContext, WeeklyReview,
} from '../src/api/types'

/** API responses shaped like the real backend (types are the contract: a field change breaks these at typecheck). */

export const DATE = '2026-10-05'

export function planItem(extra: Partial<PlanItem> = {}): PlanItem {
  return {
    id: 7, position: 1, candidate_type: 'GAP', candidate_key: 'GAP:graph.traversal', skill: 'graph.traversal', stage: 'PATTERN_DRILL',
    minutes: 35, candidate_score: 97,
    template: { key: 'dsa.pattern_drill', observation: { kind: 'ATTEMPT' }, pass_rule: 'outcome_points >= 70', output_level: 3, next_on_pass: 'TIMED' },
    problems: [{ id: 17, key: 'LEETCODE:number-of-islands', title: 'Number of Islands', difficulty: 'MEDIUM', url: null }],
    revision_item_key: null, battery_item_key: null, round_type: null,
    reason_codes: ['LARGE_GAP', 'BELOW_FLOOR', 'PATTERN_MISIDENTIFIED'],
    explanation: { target: 80, current: 51, evidence: 'LARGE_GAP, BELOW_FLOOR', priority: 57, effective: 42, expected_outcome: 'outcome_points >= 70 (L3 evidence)' },
    status: 'PENDING', skip_reason: null, observation_type: null, observation_id: null, no_evidence: false,
    carried_over_from_id: null, started_at: null, completed_at: null, ...extra,
  }
}

export function baselineItem(extra: Partial<PlanItem> = {}): PlanItem {
  return planItem({
    id: 10, candidate_type: 'BASELINE', candidate_key: 'BASE:M0-B03', skill: null, stage: 'DIAGNOSE', minutes: 30, template: null,
    problems: [], battery_item_key: 'M0-B03', reason_codes: [],
    explanation: { target: null, current: null, evidence: 'baseline battery item M0-B03', priority: null, effective: null, expected_outcome: 'measures the covered skills' },
    ...extra,
  })
}

export function baseline(done = 0): Baseline {
  const items = [
    ['M0-B01', 15, 'SELF_ASSESSMENT', 'Familiarity sweep: SELF_ASSESSMENT (NONE/SOME/SOLID) for every required skill'],
    ['M0-B02', 60, 'ATTEMPT', 'DSA diagnostic A: 2 unseen MEDIUM problems (arrays, hashing, two pointers, sliding window), timed'],
    ['M0-B03', 30, 'CODE_EXERCISE', 'Python warm-up: 5 exercises, timed 25 min'],
    ['M0-B04', 20, 'RECALL_QUIZ', 'CS quiz: DBMS, 10 closed-book questions'],
  ] as const
  return {
    items: items.map(([key, minutes, kind, name], i) => ({
      key, position: i + 1, name, minutes, observation_kind: kind, covers: ['dsa.foundations'], complete: i < done,
    })),
    battery_complete: false, battery_done: done, battery_total: 12, next_item: items[done]?.[0] ?? null, required: 123,
    assessed_required: done * 4, assessed_pct: 3, calibration_mode: true,
    phase: done === 0 ? 'NOT_STARTED' : 'IN_PROGRESS', personalization_threshold_pct: 60,
    minutes_total: 420, minutes_done: done * 35, minutes_remaining: 420 - done * 35, typical_daily_minutes: 85,
    estimated_days: Math.ceil((420 - done * 35) / 85),
  }
}

/** Baseline in a given phase (the server derives the phase; fixtures only restate its shapes). */
export function baselineIn(phase: CalibrationPhase): Baseline {
  const base = baseline(phase === 'NOT_STARTED' ? 0 : 2)
  if (phase === 'COMPLETE') {
    return { ...base, items: base.items.map((i) => ({ ...i, complete: true })), battery_complete: true, battery_done: 12, next_item: null,
      assessed_required: 98, assessed_pct: 80, calibration_mode: false, phase, minutes_done: 420, minutes_remaining: 0, estimated_days: 0 }
  }
  if (phase === 'ENOUGH_MEASURED') return { ...base, assessed_required: 75, assessed_pct: 60, phase }
  return { ...base, phase }
}

export function today(extra: Partial<Today> = {}, items: PlanItem[] = [planItem()]): Today {
  return {
    plan_date: DATE, phase: 'BUILD', weeks_left: '38.0', goal_exists: true,
    calibration: { active: false, assessed: 98, required: 123, assessed_pct: 80, battery_done: 12, battery_total: 12, next_item: null },
    readiness: { state: 'DEVELOPING', weighted_score: 74, limiting_component: 'system_design', blockers: [] },
    top_gaps: [
      { skill_key: 'graph.traversal', status: 'CRITICAL', priority: 82, primary_gap_type: 'PATTERN_RECOGNITION', focus_stage: 'PATTERN_DRILL', reason_codes: ['REPEATED_FAILURE', 'PATTERN_MISIDENTIFIED'] },
      { skill_key: 'sd.caching', status: 'HIGH', priority: 51, primary_gap_type: 'PRACTICE', focus_stage: 'GUIDED', reason_codes: ['BELOW_FLOOR'] },
    ],
    revisions: { due: 2, overdue: 1, backlog_minutes: 65, cap_minutes: 36 },
    plan: {
      id: 1, plan_date: DATE, run_id: 3, ruleset_version: 'v1', budget_minutes: 90, allocated_minutes: items.reduce((a, i) => a + i.minutes, 0),
      unallocated_minutes: 0, done_minutes: 0, phase: 'BUILD', calibration_mode: false, regenerated_count: 0, items, stop_list: [], dropped: [],
      message: { rule: 'GAP_FOCUS', text: 'Do not start dp.fundamentals today. graph.traversal is the highest-value gap.', payload: { skill: 'graph.traversal', priority: 57 } },
    },
    ...extra,
  }
}

export function calibrationToday(done = 0, items?: PlanItem[]): Today {
  return today(
    {
      phase: 'BUILD',
      calibration: { active: true, assessed: done * 4, required: 123, assessed_pct: 3, battery_done: done, battery_total: 12, next_item: baseline(done).next_item },
      readiness: { state: 'NOT_MEASURED', weighted_score: 0, limiting_component: null, blockers: [] },
      top_gaps: [], revisions: { due: 0, overdue: 0, backlog_minutes: 0, cap_minutes: 36 },
    },
    items ?? [baselineItem({ battery_item_key: baseline(done).next_item })],
  )
}

export const WEEK: WeekContext = {
  plan_date: DATE, week_start: '2026-10-05', week_end: '2026-10-11', preparation_day: 27, target_minutes: 600, practice_minutes: 510, active_days: 4,
  minutes_by_track: [
    { track: 'dsa_coding', minutes: 260, weekly_target: 210 }, { track: 'cs', minutes: 120, weekly_target: 75 },
    { track: 'system_design', minutes: 60, weekly_target: 90 }, { track: 'lld', minutes: 0, weekly_target: 75 },
  ],
  revision: { planned: 6, done: 5, completion_pct: 83 },
}

export function skill(key: string, name: string, extra: Partial<SkillWithState> = {}): SkillWithState {
  return {
    key, name, group: 'g', component: 'dsa', tier: 'T1', importance: 100, target_score: 80, floor_score: 65, required: true,
    state: {
      score: 51, effective_score: 43, level: 3, confidence: 'MEDIUM', label: 'DEVELOPING', peak_score: 51, evidence_count: 12, distinct_sources: 3,
      last_practiced_on: '2026-09-23', last_observed_on: '2026-09-23', reality_capped: false, declared_unknown: false, assessed: true,
    },
    gap: { status: 'CRITICAL', priority: 82, rank: 1, primary_gap_type: 'PATTERN_RECOGNITION', focus_stage: 'PATTERN_DRILL', focus_skill: key, reason_codes: ['REPEATED_FAILURE'], blocked_by: [], parked_reason: null },
    ...extra,
  }
}

export const SKILLS: SkillWithState[] = [
  skill('graph.traversal', 'Graphs: BFS and DFS'),
  skill('sd.caching', 'Caching strategies', {
    component: 'system_design', target_score: 80,
    state: { ...skill('x', 'x').state, effective_score: 51 },
    gap: { ...skill('x', 'x').gap!, status: 'HIGH', priority: 51, rank: 2, focus_stage: 'GUIDED', primary_gap_type: 'PRACTICE' },
  }),
  skill('arrays.traversal', 'Array traversal', {
    state: { ...skill('x', 'x').state, effective_score: 88, score: 90 },
    gap: { ...skill('x', 'x').gap!, status: 'NONE', priority: 0, rank: 9, primary_gap_type: null, focus_stage: null, reason_codes: [] },
  }),
]

export const READINESS: Readiness = {
  as_of_date: DATE, run_id: 3, ruleset_version: 'v1', state: 'DEVELOPING', simulation_eligible: false, lapsed: false, weighted_score: 74,
  limiting_component: 'system_design',
  components: [
    { key: 'dsa', name: 'DSA', score: 78, gate: 72, stretch: 80, weight: 25, assessed_pct: 90, medium_conf_pct: 70, passes_gate: true },
    { key: 'cs', name: 'CS Fundamentals', score: 68, gate: 70, stretch: 78, weight: 15, assessed_pct: 85, medium_conf_pct: 60, passes_gate: false },
    { key: 'system_design', name: 'System Design', score: 54, gate: 72, stretch: 80, weight: 18, assessed_pct: 80, medium_conf_pct: 50, passes_gate: false },
  ],
  gates: [{ gate: 'G0', passed: true, failing: 0 }, { gate: 'G2', passed: false, failing: 2 }],
  blockers: [{ gate: 'G2', subject: 'system_design', kind: 'component', actual: 54, required: 72, deficit: 18, message: 'System Design 54 < 72', skills: ['sd.caching'] }],
  all_failing: [],
}

export const HISTORY: ReadinessPoint[] = [
  { date: '2026-09-28', state: 'FOUNDATION', weighted_score: 70, limiting_component: 'cs', components: { dsa: 70, cs: 60, system_design: 50 }, blockers: 5 },
  { date: '2026-10-05', state: 'DEVELOPING', weighted_score: 74, limiting_component: 'system_design', components: { dsa: 78, cs: 68, system_design: 54 }, blockers: 4 },
]

export function revisionItem(key: string, bucket: RevisionItem['bucket'], extra: Partial<RevisionItem> = {}): RevisionItem {
  return {
    item_key: key, item_type: key.split(':')[0]!, skill: 'graph.traversal', skill_name: 'Graphs: BFS and DFS', tier: 'T1', importance: 100, parked: false,
    state: 'ACTIVE', suspend_reason: null, interval_index: 1, due_date: '2026-10-02', days_overdue: 3, lapses: 1, needs_reinforcement: false, minutes: 20,
    bucket, review_kind: 'CONCEPT_EXPLAIN', subject_ref: 'graph.traversal', last_reviewed_on: '2026-09-28', ...extra,
  }
}

export function revisionList(items: RevisionItem[]): RevisionList {
  const counts: Record<string, number> = { overdue: 0, due: 0, upcoming: 0, maintenance: 0, suspended: 0, graduated: 0 }
  for (const i of items) counts[i.bucket] = (counts[i.bucket] ?? 0) + 1
  return { backlog_minutes: 45, cap_minutes: 36, triage_threshold_minutes: 504, counts, items }
}

export const MOCK_SUMMARY: MockSummary = {
  as_of_date: DATE,
  by_type: [
    { round_type: 'DSA', rounds_60d: 1, required_60d: 3, non_self_60d: 1, latest: { date: '2026-10-01', score: 78 }, trend: [{ date: '2026-09-20', score: 70 }, { date: '2026-10-01', score: 78 }], g6_failing: ['DSA rounds in 60 days 1 < 3'] },
    { round_type: 'SYSTEM_DESIGN', rounds_60d: 1, required_60d: 2, non_self_60d: 1, latest: { date: '2026-10-01', score: 62 }, trend: [{ date: '2026-10-01', score: 62 }], g6_failing: ['SYSTEM_DESIGN latest round 62 < 65'] },
  ],
  g6_passed: false, repeated_weaknesses: [['sd.caching', 2]], final_simulations: [], g9_passed: false, g9_failing: ['0 of 3 final simulations'], simulation_eligible: false,
}

export const EMPTY_MOCK_SUMMARY: MockSummary = {
  ...MOCK_SUMMARY,
  by_type: MOCK_SUMMARY.by_type.map((t) => ({ ...t, rounds_60d: 0, non_self_60d: 0, latest: null, trend: [] })),
  repeated_weaknesses: [],
}

export const ROADMAP: RoadmapView = {
  as_of_date: DATE, baseline: { done: 12, total: 12, next_item: null, calibration_mode: false },
  tracks: [
    {
      track: 'dsa_coding', current_milestone: 'DSA-2',
      milestones: [
        { key: 'DSA-1', name: 'Python & DSA foundations', position: 1, content: null, skills: [], required_total: 18, required_done: 18, extra_exit: [], complete: true, current: false },
        { key: 'DSA-2', name: 'Core patterns', position: 2, content: '~60 problems', skills: [{ key: 'graph.traversal', required: true, level: 2, done: false }, { key: 'arrays.traversal', required: true, level: 4, done: true }], required_total: 21, required_done: 6, extra_exit: [{ text: '10 timed problems', met: false }], complete: false, current: true },
        { key: 'DSA-3', name: 'Advanced graphs, tries, DP', position: 3, content: null, skills: [], required_total: 9, required_done: 0, extra_exit: [], complete: false, current: false },
      ],
    },
    { track: 'cs', current_milestone: 'CS-1', milestones: [{ key: 'CS-1', name: 'DBMS', position: 1, content: null, skills: [], required_total: 8, required_done: 2, extra_exit: [], complete: false, current: true }] },
  ],
}

export const SKILL_DETAIL: SkillStateDetail = {
  ...skill('graph.traversal', 'Graphs: BFS and DFS'),
  prerequisites: [
    { skill: 'recursion.fundamentals', min_score: 60, effective_score: 72, satisfied: true },
    { skill: 'graph.representation', min_score: 60, effective_score: 42, satisfied: false },
  ],
  dependents: ['graph.shortest_path'], milestone: { key: 'DSA-2', name: 'Core patterns', track: 'dsa_coding' }, revision_items: [],
  focus: { stage: 'PATTERN_DRILL', template_key: 'dsa.pattern_drill', minutes: 25, pass_rule: 'outcome_points >= 70', observation_kind: 'ATTEMPT' },
  evidence: [
    { source_type: 'ATTEMPT', source_id: 8, rule: 'R1', kind: null, level: 3, outcome_points: 40, is_scoring: true, observed_on: '2026-09-23', observed_at: '2026-09-23T10:00:00Z', difficulty_bp: 10000, mapping_bp: 10000, source_key: 'attempt:8', timed: true, within_limit: false, is_unseen: true, is_weakness: false, familiarity: null, considered: true, qualifying: true },
    { source_type: 'ASSESSMENT', source_id: 3, rule: 'R2', kind: 'RECALL_QUIZ', level: 1, outcome_points: 55, is_scoring: true, observed_on: '2026-09-20', observed_at: '2026-09-20T10:00:00Z', difficulty_bp: 10000, mapping_bp: 10000, source_key: 'quiz:3', timed: false, within_limit: null, is_unseen: null, is_weakness: false, familiarity: null, considered: true, qualifying: true },
  ],
}

export const GAP_DETAIL = {
  skill_key: 'graph.traversal', name: 'Graphs: BFS and DFS', component: 'dsa', current_score: 51, effective_score: 43, target_score: 80, floor_score: 65,
  status: 'CRITICAL', priority: 82, primary_gap_type: 'PATTERN_RECOGNITION', reason_codes: ['REPEATED_FAILURE', 'PATTERN_MISIDENTIFIED', 'BELOW_FLOOR'],
  blocked_by: [], parked_reason: null, recommended_focus: { stage: 'PATTERN_DRILL', focus_skill: 'graph.traversal' },
  metrics: {
    peak_score: 51, n_fail_last5: 3, component_gate: 72, component_score: 58, depth_mean_last3: null, overconfident_rows: 0, pattern_misses_last4: 3,
    speed_median_ratio_bp: null, communication_mean_last3: null, days_since_last_practice: 12,
  },
}

export function review(extra: Partial<WeeklyReview['metrics']> = {}): WeeklyReview {
  return {
    id: 1, week_start: '2026-09-28',
    metrics: {
      week_start: '2026-09-28', week_end: '2026-10-04', active_days: 4, planned_minutes: 300, completed_minutes: 240, plan_completion_pct: 80,
      revision_completion_pct: 83, minutes_by_track: { dsa_coding: { minutes: 150, weekly_target: 210 }, cs: { minutes: 60, weekly_target: 75 } },
      top_gaps: [], gap_changes: [{ skill_key: 'sd.caching', before: 60, after: 51, delta: -9 }, { skill_key: 'graph.traversal', before: 70, after: 82, delta: 12 }],
      strongest_improvement: { skill_key: 'arrays.traversal', before: 44, after: 59, delta: 15 },
      biggest_regression: { skill_key: 'bit.manipulation', before: 50, after: 41, delta: -9 },
      readiness: { start: { state: 'FOUNDATION', weighted_score: 60 }, end: { state: 'DEVELOPING', weighted_score: 66 }, new_blockers: [], cleared_blockers: [] },
      mocks: [], backlog_minutes: 35, ...extra,
    },
    next_focus: { top_gaps: [{ skill_key: 'graph.traversal', status: 'CRITICAL', priority: 82 }, { skill_key: 'sd.caching', status: 'HIGH', priority: 51 }], tracks_below_floor: ['cs'], stop_list: [] },
    reflection: null, reflected_at: null,
  }
}

export const PROFILE: StartingProfile = {
  display_name: 'Satish', timezone: 'Asia/Kolkata', onboarding: { completed: true, completed_at: '2026-10-05T07:00:00Z' },
  experience: { years: 6, current_role: 'Backend Engineer', previous_role: 'QA Engineer' }, technologies: ['Python', 'MySQL'],
  company_profile: 'Product company',
  self_report: { strengths: ['db.core'], weaknesses: ['graph.core'], never_studied: [], recently_studied: [] },
  target: {
    role: { profile_key: 'backend_fullstack_sde2', name: 'Software Engineer — Backend/Full-Stack (SDE-2 benchmark)', seniority: 'SDE-2' },
    target_date: '2027-06-28', weekday_budgets: [90, 90, 90, 90, 90, 75, 75], weekly_minutes: 600, phase: 'BUILD', weeks_left: '38.1',
  },
  available_roles: [{ profile_key: 'backend_fullstack_sde2', name: 'Software Engineer — Backend/Full-Stack (SDE-2 benchmark)', seniority: 'SDE-2' }],
}

export const FIRST_RUN_PROFILE: StartingProfile = {
  ...PROFILE, display_name: 'Owner', onboarding: { completed: false, completed_at: null },
  experience: { years: null, current_role: null, previous_role: null }, technologies: [], company_profile: null,
  self_report: { strengths: [], weaknesses: [], never_studied: [], recently_studied: [] }, target: null,
}

export const TREE = [
  { component: 'cs', groups: [{ key: 'db.core', name: 'Databases', component: 'cs', skills: ['db.indexing'] }, { key: 'os.core', name: 'Operating systems', component: 'cs', skills: ['os.processes'] }] },
  { component: 'dsa', groups: [{ key: 'graph.core', name: 'Graphs', component: 'dsa', skills: ['graph.traversal'] }] },
]

export function roadmapItem(key: string, name: string, extra: Partial<RoadmapItem> = {}): RoadmapItem {
  return {
    skill_key: key, name, component: 'dsa', bucket: 'consolidate', health: 'developing', score: 43, target: 80, status: 'HIGH', priority: 51,
    confidence: 'MEDIUM', declared_unknown: false, primary_gap_type: 'PATTERN_RECOGNITION', focus_stage: 'PATTERN_DRILL', focus_skill: key, focus_skill_name: name,
    reason_codes: ['REPEATED_FAILURE', 'PATTERN_MISIDENTIFIED'], importance: 100, prerequisites: [], next_step_minutes: 25, ...extra,
  }
}

export function personalRoadmap(phase: CalibrationPhase = 'COMPLETE', extra: Partial<PersonalRoadmap> = {}): PersonalRoadmap {
  const focus = [
    roadmapItem('graph.traversal', 'Graphs: BFS and DFS'),
    roadmapItem('sd.caching', 'Caching strategies', { component: 'system_design', bucket: 'build', focus_stage: 'LEARN', score: 20, status: 'CRITICAL', reason_codes: ['BELOW_FLOOR'], next_step_minutes: 40,
      prerequisites: [{ skill: 'sd.basics', name: 'System design basics', score: 30, min_score: 50 }] }),
  ]
  const strong = [roadmapItem('arrays.traversal', 'Array traversal', { bucket: 'maintain', health: 'strong', score: 88, status: 'NONE', focus_stage: null, reason_codes: [], next_step_minutes: null })]
  const later = [roadmapItem('dp.core', 'Dynamic programming', { bucket: 'build', score: 12, status: 'MEDIUM', focus_stage: 'LEARN' })]
  return {
    as_of_date: DATE, calibration_phase: phase, available: true,
    based_on: { role: PROFILE.target!.role, target_date: '2027-06-28', weeks_left: '38.1', phase: 'BUILD', measured_skills: 98, required_skills: 123, blocked_skills: 4, overdue_reviews: 1 },
    focus_now: focus,
    sections: {
      build: { count: 2, items: [focus[1]!, later[0]!] }, consolidate: { count: 1, items: [focus[0]!] }, sharpen: { count: 0, items: [] },
      maintain: { count: 1, items: strong }, parked: { count: 1, items: [roadmapItem('trie.core', 'Tries', { bucket: 'parked', status: 'PARKED', health: 'parked' })] },
      unmeasured: { count: 25, items: [] }, later: { count: 1, items: later },
    },
    why: [{
      skill_key: 'graph.traversal', name: 'Graphs: BFS and DFS', component: 'dsa', score: 43, target: 80, importance: 100, priority: 82,
      reason_codes: ['REPEATED_FAILURE', 'PATTERN_MISIDENTIFIED'], prerequisites: [],
      metrics: { ...GAP_DETAIL.metrics },
    }],
    changes: { since: '2026-10-04', changed: false, entered: [], left: [] }, ...extra,
  }
}

export function currentState(extra: Partial<CurrentState> = {}): CurrentState {
  return {
    as_of_date: DATE, calibration_phase: 'COMPLETE', counts: { strong: 1, developing: 1, critical: 1, unknown: 25, parked: 1, total: 29 },
    strong: { count: 1, items: [roadmapItem('arrays.traversal', 'Array traversal', { health: 'strong', score: 88, status: 'NONE' })] },
    developing: { count: 1, items: [roadmapItem('graph.traversal', 'Graphs: BFS and DFS')] },
    critical: { count: 1, items: [roadmapItem('sd.caching', 'Caching strategies', { health: 'critical', status: 'CRITICAL', score: 20 })] },
    unknown: { count: 25, items: [] },
    self_reported: [
      { group_key: 'db.core', name: 'Databases', component: 'cs', claims: ['STRONG'], measured: 1, total: 2,
        skills: [{ skill_key: 'db.indexing', name: 'Indexing', score: 82, target: 80, confidence: 'HIGH', status: 'NONE', declared_unknown: false }] },
      { group_key: 'graph.core', name: 'Graphs', component: 'dsa', claims: ['WEAK', 'RECENTLY_STUDIED'], measured: 0, total: 1, skills: [] },
    ],
    ...extra,
  }
}
