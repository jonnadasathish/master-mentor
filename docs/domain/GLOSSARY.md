# Master Mentor — Glossary (Spec v2, ruleset `v1`)

Every term below has exactly one meaning. Code identifiers, API fields, UI labels and documents must use these meanings. When a document needs a different concept, it gets a different word. If a term is not here, it is not a domain term.

Conventions: `snake_case` is a field or code identifier; `UPPER_CASE` is an enum value; "≥" and "≤" are inclusive.

---

## Benchmark and structure

| Term | Definition |
|---|---|
| **Role Profile** | The internal target benchmark (`backend_fullstack_sde2`) that defines interview rounds, readiness components, weights, gates, and per-skill tier. Owned by `ROLE_PROFILE.md` + `seed/role_profiles/*.yaml`. It is **not** a claim about any company's loop. |
| **Interview Round** | One round of the declared loop (e.g. `DSA_1`, `SYSTEM_DESIGN`). Each round has a **Round Type** (`DSA`, `CS`, `LLD`, `SYSTEM_DESIGN`, `BEHAVIORAL`, `PROJECT_DEEP_DIVE`) that maps to fixed Readiness Components (`DSA` → `dsa` + `coding`; every other type → its one component). `FINAL_SIMULATION` has no round type; it is gate G9. |
| **Readiness Component** (Component) | One of seven scored areas: `dsa`, `coding`, `cs`, `lld`, `system_design`, `behavioral`, `project`. Every skill belongs to exactly one component. |
| **Skill Group** | A non-scored parent node in the skill graph (e.g. `cs.dbms`). Used for navigation and roll-up display only. Has no target, gap, or evidence. |
| **Skill** | A scored, gap-bearing node in the skill graph, identified by a stable `skill_key` (e.g. `graph.traversal`). Has exactly one parent Skill Group, one Component, zero or more Prerequisites, and a Tier from the Role Profile. Skills are the only units that carry Skill State, Gaps, and Targets. |
| **Topic** | A free-text label listed under a skill (e.g. `exceptions` under `python.core_syntax`) used for content and search. Topics are never scored. |
| **Pattern** | A DSA Skill with `is_pattern = true` (e.g. `sliding_window.core`). Patterns get PATTERN revision items and PATTERN_RECOGNITION gap checks. `pattern_identified` outcomes produce evidence on the meta-skill `dsa.pattern_recognition` (which is not itself a pattern). |
| **Competency** | A Behavioral Skill (`behavioral.*`, `communication.*`). Behavioral stories link to one or more competencies. |
| **Prerequisite** | A directed edge "skill A requires skill B at `min_score`". The only relationship type between skills. The graph of prerequisites is acyclic. |
| **Prerequisite satisfied** | `prereq.score ≥ min_score` (uses `score`, not `effective_score`). An unassessed prerequisite is **not** satisfied. |
| **Tier** | Role-profile classification of a skill: `T1` critical, `T2` core, `T3` supporting, `T4` optional. A tier fixes importance, target, and floor. |
| **Required Skill** | A skill of tier T1, T2 or T3. T4 skills are optional and excluded from readiness. |
| **Critical Skill** | A skill of tier T1. |
| **Importance** | Integer 0–100 from the tier (T1 100, T2 75, T3 50, T4 20). |
| **Target Score** | Integer 0–100 from the tier (T1 80, T2 75, T3 65, T4 50). The score the benchmark requires. |
| **Floor** | Minimum acceptable `effective_score` (T1 65, T2 55, T3/T4 none). Falling below it adds pressure and, for T1, fails a readiness gate. |
| **Track** | A weekly time-allocation bucket used by the mentor: `dsa_coding`, `cs`, `lld`, `system_design`, `behavioral_project`, `mock`. Not the same as a Component. |
| **Roadmap Milestone** | An ordered step within a Track (e.g. `DSA-2 Core patterns`) with evidence-based exit criteria. The current milestone of a track is the first one whose exit criteria are not met. |

## Recording what happened

| Term | Definition |
|---|---|
| **Observation** | Any authoritative, append-only raw record of activity: a Problem Attempt, an Assessment, a Revision Review, or a Mock Round. Observations are never edited. Corrections create a new observation with `supersedes_id`. |
| **Attempt** (Problem Attempt) | An observation of one try at one catalog problem (`problem_attempts`). |
| **Assessment** | An observation of any non-problem activity: recall quiz, explanation, design exercise, machine coding, story rehearsal, project walkthrough, study session, self-assessment. Has a `kind`, conditions (`notes_used`, `timed`, …) and per-skill `outcome_points`. |
| **Mock** | A mock interview session consisting of one or more Mock Rounds. Has `source` `SELF`, `PEER`, or `PLATFORM`. |
| **Mock Round** | One round inside a Mock, with a `round_type`, a `round_score` 0–100, a rubric, and per-skill outcomes. |
| **Final Simulation** | A Mock flagged `is_final_simulation = true` that satisfies the round composition in `READINESS_MODEL.md` §6. |
| **Outcome** | The result of an attempt or review: `PASS`, `PARTIAL`, `FAIL`. No other vocabulary (no "solved", "success"). |
| **Outcome Points** | Integer 0–100 measuring how well one observation succeeded for one skill (table in `EVIDENCE_MODEL.md` §4). |
| **Self-rating** | The user's own 1–5 rating (`self_rating_before`, `self_rating_after`). Stored on observations. **Never** contributes to score, level, or evidence confidence. Used only for the CONFIDENCE gap type and messages. |
| **Declared Unknown** | A self-assessment with `familiarity = NONE`. The only self-report that changes state: it marks a skill assessed at score 0 (self-reports may lower state, never raise it). |
| **Starting Profile** | The user's own context: experience, current stack, target company note, and self-reported topic claims (strong, weak, never studied, recently studied). Configuration (`starting_profile`), **not evidence**: no engine reads it. The goal (target role, date, weekday budgets) stays in `goals`. |
| **Self-reported Context** | Everything in the Starting Profile that describes skill. Always labelled "not yet verified" and shown beside measured values. Distinct from a Declared Unknown, which is an observation. |
| **Evidence** | A derived, rebuildable row: the contribution of one observation to one skill under one ruleset version (`evidence` table). Carries `level`, `outcome_points`, weights, `source_key`. Evidence is a projection, never edited by hand. |
| **Evidence Level** (Level) | The L0–L7 rung an evidence row demonstrates (L0 Exposed, L1 Recall, L2 Guided, L3 Independent, L4 Timed, L5 Explain, L6 Transfer, L7 Interview). A skill's Level is the highest rung it has *qualified* for. See `EVIDENCE_MODEL.md`. |
| **Source Key** | The identity used for diversity: `problem:<id>`, `prompt:<key>`, `story:<id>`, `project:<key>`, `exercise:<key>`, `drill:<key>`, `battery:<key>`, `mock_round:<id>`. Two evidence rows with the same source key are not diverse. |

## Derived state

| Term | Definition |
|---|---|
| **Skill State** | The derived current condition of one skill: `score`, `level`, `confidence`, `effective_score`, `peak_score`, counts and dates. Rebuilt from evidence on every Mentor Run. |
| **Unassessed** | A skill with no evidence row of level ≥ L1 and no Declared Unknown. `score` is `null`. |
| **Score** | Integer 0–100 skill score computed from level band and quality (`EVIDENCE_MODEL.md` §7). |
| **Confidence** | Evidence confidence: `NONE`, `LOW`, `MEDIUM`, `HIGH`, measuring how much evidence backs the score. It never means self-rating. |
| **Effective Score** | `max(score − uncertainty_penalty[confidence], 0)`. The value used by gaps, floors, components, and gates. |
| **Peak Score** | The score computed from all-time evidence with no recency window. Used for RETENTION. |
| **Calibration Phase** | The user-facing status of the baseline: `NOT_STARTED`, `IN_PROGRESS`, `ENOUGH_MEASURED` (battery open but at least `CALIBRATION_MIN_ASSESSED_PCT` of required skills assessed), `COMPLETE` (every battery item done). Derived; it does not change the mentor's rules. |
| **Personal Roadmap** | A read-only grouping of the gap engine's output: build, consolidate, sharpen, maintain, parked, not measured; plus "focus now" (top 5 actionable, unblocked). No second roadmap engine exists. |
| **Gap** | The derived shortfall of one skill against its target for the active goal, with severity, priority, status, types, and reasons (`gap_states`). |
| **Raw Gap** | `max(target_score − effective_score, 0)`. |
| **Severity** | `raw_gap × importance / 100` (Decimal). |
| **Pressure** | Basis-point multiplier ≥ 10000 built from failure, mocks, gates, floors, recency (`GAP_ENGINE.md` §5). |
| **Priority** | Integer 0–100: `min(100, round_half_up(severity × pressure_bp / 10000))`. For unassessed skills it is the assessment priority. Absolute scale, never normalized against other skills. |
| **Gap Status** | One of `CRITICAL` (priority ≥ 60), `HIGH` (40–59), `MEDIUM` (25–39), `LOW` (10–24), `NONE` (< 10), or the overriding statuses `UNASSESSED`, `BLOCKED`, `PARKED`. |
| **Gap Type** | The diagnosed *kind* of shortfall: `UNASSESSED`, `PREREQUISITE`, `KNOWLEDGE`, `RETENTION`, `PATTERN_RECOGNITION`, `PRACTICE`, `CONFIDENCE`, `SPEED`, `DEPTH`, `COMMUNICATION`, `INTERVIEW_EXECUTION`, `EXPERIENCE`, `LEVEL_UP`. A gap has one primary type (first match in precedence order) and a list of all matching types. |
| **Reason Code** | A fixed `UPPER_CASE` code explaining a computed value (`REPEATED_FAILURE`, `BELOW_FLOOR`, …). Full list in `GAP_ENGINE.md` §9 and `MENTOR_ENGINE.md` §9. |
| **Blocked** | Gap status of a skill with at least one unsatisfied prerequisite. Blocked skills get no missions; their priority flows to the blocking prerequisite (`UNLOCKS`). |
| **Parked** | Gap status of a skill deliberately excluded from missions because of the Prep Phase or feasibility. Parked skills still count in readiness. |
| **Recommended Focus** | The Mission Stage the gap engine recommends for a gap (e.g. `TIMED`). It is derived from the primary gap type and level. |

## Time and planning

| Term | Definition |
|---|---|
| **as_of_date** | The local calendar date (user timezone) that every engine receives as an explicit input. Domain code never reads the clock. |
| **Prep Phase** | Deadline mode from `weeks_left = days/7` (Decimal): `BUILD` (> 12 or no target date), `CONSOLIDATE` (4 < w ≤ 12), `SHARPEN` (≤ 4, including a past target date). |
| **Calibration Mode** | Mentor mode active while the baseline battery is incomplete **or** fewer than 60% of required skills are assessed. While the battery is incomplete the plan is due revisions + battery items; afterwards diagnostics get up to 60% of the budget. |
| **Mission** | A concrete, time-boxed unit of practice for one skill (or one revision item / mock), instantiated from a Mission Template, with a stage, minutes, pass criteria, and the evidence it must produce. A mission exists only as a Plan Item. |
| **Mission Template** | A catalog definition keyed by `(component, stage)` with optional gap-type specialization (`MISSION_LIBRARY.md`). |
| **Mission Stage** | The practice mode of a mission: `DIAGNOSE`, `LEARN`, `RECALL`, `GUIDED`, `INDEPENDENT`, `TIMED`, `EXPLAIN`, `TRANSFER`, `SIMULATE`, `PATTERN_DRILL`, `THINK_ALOUD`, `REINFORCE`, plus `REVISION` for scheduled revision items. Each stage targets a specific Evidence Level (`MISSION_LIBRARY.md` §2). |
| **Candidate** | Anything the mentor could schedule today, typed `BASELINE`, `GAP` (including LEARN-stage new topics), `DIAGNOSTIC`, `REVISION`, `MAINTENANCE`, `MOCK`, `FINAL_SIMULATION`, or `FOLLOW_UP`, with a candidate score on one unified scale. |
| **Daily Plan** | The frozen, ordered list of Plan Items for one local date, generated at the first request of that date. Regenerated only by explicit user action. |
| **Plan Item** | One scheduled mission in a Daily Plan, with status `PENDING`, `DONE`, `SKIPPED`, `DEFERRED`, or `DISCARDED` (removed by an explicit regenerate). |
| **Stop List** | Skills the mentor tells the user to stop spending time on (one entry per skill): PARKED, OVER_TARGET, and STUDIED_NOT_TESTED skills. |
| **Revision** | The spaced-retrieval subsystem. A **Revision Item** is one schedulable thing to re-test (e.g. `PROBLEM:42`) with type, interval index, due date, lapses, and state. A **Revision Review** is the observation of performing it. |
| **Lapse** | A FAIL outcome on a Revision Review. |
| **Leech** | A revision item with `lapses ≥ 3`. It is suspended and converted into skill-level remediation. |
| **Weekly Review** | The auto-generated summary of one Monday-to-Sunday local week (metrics, gap movement, readiness delta, next-week focus) plus the user's reflection. |

## Readiness

| Term | Definition |
|---|---|
| **Component Score** | Importance-weighted mean of `effective_score` over the required skills of a component (unassessed = 0). |
| **Weighted Readiness Score** | Weight-sum of component scores. Displayed only. **Never decides a readiness state.** |
| **Gate** | A boolean readiness condition (`G0`–`G9`) defined in `READINESS_MODEL.md`. |
| **Blocker** | One failing (gate, subject) pair with actual, required, deficit and message; failing conditions of the same subject merge. Blockers explain why the readiness state is not higher. |
| **Readiness State** | `NOT_MEASURED`, `FOUNDATION`, `DEVELOPING`, `INTERVIEW_READY`, `STRONG`. Determined only by gates. |
| **Lapsed** | Flag set when the readiness state drops from `INTERVIEW_READY`/`STRONG` to a lower state. |
| **Simulation Eligible** | Flag: gates G0–G8 pass. The mentor schedules final simulations only when this flag is set. Any valid final simulation counts toward G9. |

## System

| Term | Definition |
|---|---|
| **Mentor Run** | One deterministic recalculation (`mentor_runs` row): inputs `as_of_date`, `ruleset_version`, `seed_version`, active goal, `input_hash`; outputs skill states, gaps, readiness, and revision projection. Triggered synchronously after every observation write and on plan generation. |
| **Ruleset Version** | The version string (`v1`) of all formula constants in `backend/app/domain/rulesets/`. Any change to a constant or rule requires a new version and a `DECISION_LOG.md` entry. Stored on every derived row. |
| **Seed Version** | The version string (`seed-v1`) of the catalog YAML (skills, profile, problems, templates, roadmap). |
| **Audit Event** | An append-only `audit_log` row for every state-changing user action (goal change, correction, suspension, plan regeneration, story edit). |

## Retired v1 terms (do not use)

| v1 term | Replaced by |
|---|---|
| `developer`, `developer_id` | the single user (no user id in domain tables) |
| `solved/partial/failed`, `success` | Outcome `PASS/PARTIAL/FAIL` |
| `confidence` (1–5 on attempts) | Self-rating |
| `base strength`, `evidence quality modifiers` | Evidence Level + Outcome Points + weights |
| `criticality` | Tier / Importance |
| `recency_risk` multiplier on all gaps | `RETENTION_RISK` pressure term (bounded) |
| `missions` table, `daily_plan_items` | Plan Item |
| `state_snapshots` | Mentor Run + daily snapshots |
| "Interview Ready" skill label | skill label `INTERVIEW_GRADE` (readiness state `INTERVIEW_READY` is only a readiness term) |
| Roadmap "Level 0–9" | Roadmap Milestone (the word Level is reserved for evidence levels) |
