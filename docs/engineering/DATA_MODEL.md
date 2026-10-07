# Master Mentor — Data Model & Database Rules (Spec v2)

MySQL 8, InnoDB, `utf8mb4`. Every schema change is an Alembic migration. Single user, so **no `user_id` columns** (decision D-018). This document absorbs the former `DATABASE_RULES.md`.

## 1. Table classes

| Class | Tables | Mutability | Rebuild |
|---|---|---|---|
| **Catalog** | `skill_groups`, `skills`, `skill_prerequisites`, `role_profiles`, `role_skill_targets`, `problems`, `problem_skills`, `mission_templates`, `roadmap_milestones`, `roadmap_milestone_skills`, `baseline_items`, `catalog_loads` | written only by the seed loader (`make seed`): validate first, then upsert by natural key in one transaction | from `seed/*.yaml` |
| **Profile** | `app_settings`, `starting_profile`, `goals` | `app_settings` updated with an audit event; `goals` are **versioned**: any change inserts a new version row | — |
| **Content** | `behavioral_stories`, `story_competencies`, `projects`, `assessment_prompts` | editable content with an audit event; never evidence by itself | — |
| **Activity** (authoritative) | `problem_attempts`, `attempt_mistakes`, `assessments`, `assessment_skills`, `mocks`, `mock_rounds`, `mock_round_skills`, `revision_item_actions` | **append-only**; corrections insert a row with `supersedes_id` | — |
| **Decisions** | `mentor_runs`, `daily_plans`, `plan_items`, `weekly_reviews` | written once; status changes on `plan_items` and reflections are audited | not rebuilt (they are history) |
| **Derived** | `evidence`, `skill_states`, `gap_states`, `revision_items`, `readiness_snapshots`, `skill_daily_snapshots` | overwritten by mentor runs | from activity + decisions + catalog |
| **System** | `audit_log` | append-only | — |

There is no `revision_reviews` table. A revision review **is** the observation (attempt or assessment) carrying `revision_item_key`. Its outcome is derived.

## 2. Catalog

| Table | Columns (type) | Constraints |
|---|---|---|
| `skill_groups` | `id` PK, `group_key` VARCHAR(64), `name`, `component` ENUM(dsa, coding, cs, lld, system_design, behavioral, project), `position` (seed order), `seed_version` | UNIQUE `group_key`; a group removed from the seed is kept (inactive skills may reference it) |
| `skills` | `id` PK, `skill_key` VARCHAR(64), `name`, `group_id` FK, `component` ENUM, `is_pattern` BOOL, `evidence_kinds` JSON, `topics` JSON, `position` (seed order), `active` BOOL, `seed_version` | UNIQUE `skill_key`; a skill removed from the seed is deactivated, never deleted |
| `skill_prerequisites` | `skill_id` FK, `prereq_skill_id` FK, `min_score` SMALLINT, `position` (order in the skill's list) | PK (skill_id, prereq_skill_id); CHECK `min_score IN (30,45,60)`; CHECK `skill_id <> prereq_skill_id`; acyclicity and depth ≤ 6 are checked by the seed validator. This is the ONLY skill relationship (no enables/related/parent types; parent = `group_id`) |
| `role_profiles` | `id`, `profile_key`, `name`, `seniority`, `config_json` (loop, components, tiers, tracks, gate parameters, final simulation), `seed_version` | UNIQUE `profile_key` |
| `role_skill_targets` | `profile_id`, `skill_id`, `tier` ENUM(T1..T4), `importance`, `target_score`, `floor_score` (SMALLINT) | PK (profile_id, skill_id). `required` is derived from the tier (`config_json.tiers[tier].required`), not stored |
| `problems` | `id`, `platform` ENUM(LEETCODE, OTHER), `platform_key`, `title`, `url`, `difficulty` ENUM(EASY, MEDIUM, HARD), `expected_minutes` SMALLINT NULL, `is_canonical` BOOL, `active` BOOL, `seed_version` | UNIQUE (platform, platform_key) |
| `problem_skills` | `problem_id`, `skill_id`, `mapping_weight_bp` SMALLINT | PK (problem_id, skill_id); CHECK IN (5000, 10000); exactly one 10000 per problem (validator) |
| `mission_templates` | `template_key`, `component`, `stages` JSON, `gap_types` JSON NULL, `applies_to` JSON NULL, `item_type` NULL, `minutes` SMALLINT NULL, `minutes_rule` VARCHAR NULL (for revision/mock templates whose minutes depend on the item or round), `min_budget` SMALLINT NULL, `difficulty` NULL, `needs_problem` BOOL, `observation_json`, `pass_rule`, `partial_rule` NULL, `output_level` TINYINT, `next_on_pass`, `next_on_fail`, `seed_version` | PK `template_key` |
| `roadmap_milestones` | `id`, `milestone_key`, `track`, `track_position`, `position`, `name`, `extra_exit_json`, `content` TEXT NULL, `starts_when` NULL, `seed_version` | UNIQUE `milestone_key`; INDEX (track, position) — ordering uniqueness is enforced by the validator so reorderings never collide mid-transaction |
| `roadmap_milestone_skills` | `milestone_id`, `skill_id` | PK `skill_id` (each skill in exactly one milestone) |
| `baseline_items` | `item_key`, `position`, `name`, `minutes`, `observation_kind`, `covers_json`, `seed_version` | PK `item_key` |
| `catalog_loads` | `id`, `seed_version`, `catalog_fingerprint` CHAR(64), `file_fingerprints_json`, `counts_json` (inserted/updated/unchanged/deactivated/deleted per table), `loaded_at` UTC | one row per load that changed the catalog; the latest row = the loaded catalog (D-044) |

Personal problems are added at runtime (`POST /problems`, `platform = OTHER` or `LEETCODE`). They carry `seed_version = 'user'`, use ids ≥ 1,000,000 (the seed validator restricts seed ids to 1–999,999), and are never touched by the seed loader. The loader also refuses a seed problem whose (platform, platform_key) equals a personal problem's (D-050). Stable problem key = `"<PLATFORM>:<platform_key>"`.

## 3. Profile and content

| Table | Columns | Notes |
|---|---|---|
| `app_settings` | `id` = 1, `timezone` (IANA), `display_name`, `created_at` | CHECK `id = 1` |
| `starting_profile` | `id` = 1, `onboarding_completed_at` (first-run flag), `experience_years`, `current_role`, `previous_role`, `technologies_json` (≤ 30), `company_profile`, `self_report_json` `{strengths, weaknesses, never_studied, recently_studied}` (skill-group keys), `updated_at` | CHECK `id = 1`. Configuration like `app_settings` (kept by dev-reset, exported, imported separately). **Never evidence**; no engine reads it. Bootstrapped by migration `0011` (marked complete when a goal already exists). Changes audited with before/after (`UPDATE_STARTING_PROFILE`, `COMPLETE_ONBOARDING`, `REDO_ONBOARDING`). |
| `goals` (migration `0005`) | `id`, `role_profile_id` FK, `target_date` DATE NULL, `weekday_budgets_json` (7 ints, Mon..Sun; default 90,90,90,90,90,75,75 = 600), `valid_from` DATE, `valid_to` DATE NULL, `created_at` | Never updated except to close `valid_to`. A change inserts a new row valid from the change date and closes the previous one. Engines use the version valid on `as_of_date` (`valid_from ≤ as_of < valid_to`), so replays of past dates see past goals. Validator: no overlapping versions |
| `behavioral_stories` | `id`, `title`, `situation`, `task`, `action`, `result`, `metric`, `learning`, `created_at`, `updated_at`, `archived_at` | edits audited |
| `story_competencies` | `story_id`, `skill_id`, `position` | PK (story_id, skill_id); UNIQUE (story_id, position); skill must be behavioral/communication; position 1 = owning skill for revision |
| `projects` | `id`, `project_key`, `name`, `summary`, `architecture_notes`, `created_at`, `updated_at` | UNIQUE `project_key` |
| `assessment_prompts` | `id`, `prompt_key`, `skill_id`, `kind`, `prompt_text`, `answer_key_text`, `created_at` | UNIQUE `prompt_key`; the source key for concept evidence |

## 4. Activity (append-only)

### `problem_attempts`

| Column | Type | Rule |
|---|---|---|
| `id` | BIGINT PK | |
| `problem_id` | FK | |
| `attempted_on` | DATE | local date (user timezone); may be backdated |
| `attempted_at` | DATETIME (UTC) | |
| `mode` | ENUM(PRACTICE, DIAGNOSTIC, BASELINE, REVISION, SIMULATION) | |
| `outcome` | ENUM(PASS, PARTIAL, FAIL) | |
| `seen_elsewhere` | BOOL | user had seen this problem outside the app |
| `hints_used` | TINYINT | ≥ 0 |
| `solution_viewed` | BOOL | |
| `pattern_identified` | BOOL NULL | correct approach named **before** any hint |
| `timed` | BOOL | |
| `time_limit_seconds`, `time_seconds` | INT NULL | |
| `explanation_score` | TINYINT NULL | 0–10 |
| `complexity_correct`, `followup_solved` | BOOL NULL | |
| `execution_rubric_json` | JSON NULL | {clarification, think_aloud, testing, time_management, optimization}: 0–10 each |
| `self_rating_before`, `self_rating_after` | TINYINT NULL | 1–5; never used for score |
| `notes` | TEXT | |
| `revision_item_key` | VARCHAR(96) NULL | set when this is a revision review |
| `battery_item_key` | VARCHAR(16) NULL | set when this completes a baseline battery item |
| `client_request_id` | VARCHAR(64) NULL | UNIQUE when present (double-submit protection) |
| `plan_item_id` | FK NULL | |
| `supersedes_id` | FK self NULL | correction chain |
| `created_at` | DATETIME (UTC) | |

`attempt_mistakes(attempt_id, mistake_code ENUM(WRONG_PATTERN, NO_APPROACH, MISREAD_PROBLEM, EDGE_CASE_MISSED, OFF_BY_ONE, IMPLEMENTATION_BUG, LANGUAGE_SYNTAX, DATA_STRUCTURE_API, WRONG_COMPLEXITY, TIME_OVERRUN))`, PK (attempt_id, mistake_code). Mistakes are returned in this vocabulary order.

Implemented in Slice 3 (`0003_activity`): CHECKs on hints ≥ 0, time ≥ 0, explanation 0–10, ratings 1–5; `supersedes_id` is UNIQUE (linear correction chains); `client_request_id` is UNIQUE; `revision_item_key`, `battery_item_key`, `plan_item_id` exist as nullable columns without FKs until their tables arrive. Indexes: (problem_id, attempted_on), (attempted_on), (attempted_at), (revision_item_key). The evidence engine's per-skill query goes `skills → problem_skills(skill_id) → problem_attempts(problem_id, attempted_on)`, and every step is index-backed (verified with EXPLAIN in `tests/db/test_activity_queries.py`).

### `assessments` + `assessment_skills`

| Column | Type |
|---|---|
| `id`, `kind` | ENUM(STUDY_SESSION, SELF_ASSESSMENT, RECALL_QUIZ, PATTERN_DRILL, CONCEPT_EXPLAIN, CODE_EXERCISE, ESTIMATION_DRILL, SD_DESIGN, LLD_DESIGN, MACHINE_CODING, STORY_REHEARSAL, PROJECT_WALKTHROUGH, APPLIED_TASK) |
| `observed_on` DATE, `observed_at` DATETIME UTC, `mode` | mode ENUM as attempts |
| `source_key` | VARCHAR(96): `prompt:…`, `exercise:…`, `story:…`, `project:…`, `battery:…`, `drill:…` |
| conditions | `notes_used`, `reference_used`, `timed`, `peer_evaluated`, `applied`, `unseen_variant` BOOL; `hints_used` TINYINT; `time_limit_seconds`, `time_seconds` INT NULL; `difficulty` ENUM default MEDIUM |
| measures | `followup_points`, `communication_points` TINYINT NULL; `rubric_json` |
| `familiarity` | ENUM(NONE, SOME, SOLID) NULL (SELF_ASSESSMENT only) |
| `study_minutes` | SMALLINT NULL |
| `self_rating_before`, `self_rating_after`, `notes`, `revision_item_key`, `battery_item_key`, `client_request_id`, `plan_item_id`, `supersedes_id`, `created_at` | as attempts |

`assessment_skills(assessment_id, skill_id, outcome_points TINYINT NULL, mapping_weight_bp SMALLINT, is_pattern_target BOOL)`, PK (assessment_id, skill_id). `outcome_points` is NULL only for STUDY_SESSION / SELF_ASSESSMENT.

Implemented in migration `0004_evidence` (Slice 4). Indexes: `observed_on`, `(kind, observed_on)`, `source_key`, `revision_item_key`, `battery_item_key`; CHECKs on ratings, points and times. Capture rules: D-055.

### Mocks

Implemented in migration `0009_mocks_content` (with the content tables of §3). `mocks` also stores `plan_item_id`; `mock_rounds` also stores `communication_points`.

| Table | Columns |
|---|---|
| `mocks` | `id`, `occurred_on` DATE, `occurred_at`, `source` ENUM(SELF, PEER, PLATFORM), `is_final_simulation` BOOL, `notes`, `client_request_id` NULL UNIQUE, `supersedes_id`, `created_at`. A mock has one `occurred_on`, so all its rounds share one local day (this satisfies the final-simulation `max_span_days: 1`) |
| `mock_rounds` | `id`, `mock_id`, `position`, `round_type` ENUM(DSA, CS, LLD, SYSTEM_DESIGN, BEHAVIORAL, PROJECT_DEEP_DIVE), `duration_minutes`, `round_score` TINYINT, `rubric_json` |
| `mock_round_skills` | `round_id`, `skill_id`, `outcome_points` TINYINT, `is_weakness` BOOL; PK (round_id, skill_id) |

### `revision_item_actions`

`id`, `item_key`, `action` ENUM(SUSPEND, RESUME), `reason` ENUM(MANUAL, BACKLOG_TRIAGE), `action_on` DATE, `run_id` NULL, `created_at`. These are recorded decisions replayed by the revision projection. Implemented in migration `0006_revision` (index `(item_key, action_on)`).

## 5. Decisions

| Table | Columns | Constraints |
|---|---|---|
| `mentor_runs` | `id`, `run_at` UTC, `as_of_date`, `trigger` ENUM(OBSERVATION, PLAN, REBUILD, CORRECTION, GOAL), `goal_id`, `ruleset_version`, `seed_version`, `input_hash` CHAR(64), `calibration_mode`, `phase`, `duration_ms` | INDEX (as_of_date, id) |
| `daily_plans` | `id`, `plan_date` DATE, `run_id`, `goal_id`, `budget_minutes`, `allocated_minutes`, `phase`, `calibration_mode`, `message_rule`, `message_text`, `message_payload_json`, `stop_list_json`, `dropped_json`, `input_hash`, `regenerated_count`, `generated_at` | **UNIQUE `plan_date`** |
| `plan_items` | `id`, `plan_id`, `position`, `candidate_type` ENUM(BASELINE, GAP, DIAGNOSTIC, REVISION, MAINTENANCE, MOCK, FINAL_SIMULATION, FOLLOW_UP), `candidate_key`, `skill_id` NULL, `template_key`, `stage`, `problem_ids_json`, `revision_item_key` NULL, `battery_item_key` NULL, `minutes`, `candidate_score`, `reason_codes_json`, `explanation_json`, `status` ENUM(PENDING, DONE, SKIPPED, DEFERRED, DISCARDED), `skip_reason` ENUM(NO_TIME, TOO_HARD, NOT_RELEVANT, OTHER) NULL, `observation_type` ENUM(ATTEMPT, ASSESSMENT, MOCK) NULL, `observation_id` NULL, `no_evidence` BOOL, `carried_over_from_id` NULL, `completed_at` | UNIQUE (plan_id, position) |
| `weekly_reviews` | `id`, `week_start` DATE, `run_id`, `metrics_json`, `next_focus_json`, `reflection_json` NULL, `generated_at`, `reflected_at` | UNIQUE `week_start` |

Implemented in migration `0007_plans`; `daily_plans` also stores `ruleset_version`; `plan_items` also stores `round_type` and `status_changed_at`. `plan_items` also has `started_at` DATETIME NULL (set by `/plan/items/{id}/start`; informational only). `DISCARDED` marks PENDING items removed by an explicit regenerate. They are kept for history, not deleted.

## 6. Derived (rebuildable)

| Table | Key | Columns |
|---|---|---|
| `evidence` | UNIQUE (source_type, source_id, skill_id, ruleset_version) | `id`, `source_type` ENUM(ATTEMPT, ASSESSMENT, MOCK_ROUND), `source_id`, `skill_id`, `rule` ENUM(MAPPED, DERIVED, MISTAKE, ASSESSMENT, MOCK), `kind` NULL (assessment kind), `level` TINYINT, `outcome_points` TINYINT NULL, `is_scoring` BOOL, `observed_on`, `observed_at`, `difficulty_bp`, `mapping_bp`, `is_primary`, `source_key`, `timed` BOOL, `time_ratio_bp` INT NULL, `within_limit` NULL, `depth_points` NULL, `communication_points` NULL, `self_rating_before` NULL, `pattern_identified` NULL, `is_unseen` NULL, `is_weakness`, `familiarity` NULL, `study_minutes` NULL, `ruleset_version` |
| `skill_states` | PK `skill_id` | `run_id`, `as_of_date`, `score` NULL, `level` NULL, `quality` DECIMAL(9,4) NULL, `confidence` ENUM(NONE, LOW, MEDIUM, HIGH), `effective_score` NULL, `peak_score` NULL, `evidence_count`, `distinct_sources`, `last_practiced_on` NULL, `last_observed_on` NULL, `label`, `reality_capped` BOOL, `declared_unknown` BOOL, `considered_evidence_json`, `qualifying_evidence_json` (`[source_type, source_id, skill]` references: traceability), `ruleset_version` |
| `gap_states` | PK `skill_id` | `run_id`, `goal_id`, `as_of_date`, `status`, `priority`, `rank`, `raw_gap`, `severity` DECIMAL(7,2), `pressure_bp`, `primary_gap_type`, `gap_types_json`, `reason_codes_json`, `blocked_by_json`, `parked_reason`, `focus_stage`, `focus_skill`, `metrics_json`, `evidence_json`, `ruleset_version` (migration `0005_goals_gaps`) |
| `revision_items` | PK `item_key` | `item_type`, `skill_id`, `subject_ref`, `ladder` ENUM(STANDARD, MOCKW), `state` ENUM(ACTIVE, SUSPENDED, GRADUATED), `suspend_reason` ENUM(LEECH, BACKLOG_TRIAGE, MANUAL) NULL, `interval_index`, `due_date` DATE NULL (graduated: next maintenance check or NULL), `lapses`, `needs_reinforcement`, `minutes`, `created_on`, `last_reviewed_on`, `suspended_on`, `run_id` (migration `0006_revision`) |
| `readiness_snapshots` (migration `0008`) | PK `snapshot_date` | `run_id`, `state`, `weighted_score`, `limiting_component`, `simulation_eligible`, `lapsed`, `components_json`, `gates_json`, `blockers_json`, `all_failing_json` |
| `skill_daily_snapshots` | PK (snapshot_date, skill_id) | `score`, `effective_score`, `level`, `confidence`, `priority`, `status` (weekly gap changes, trends) |

Daily snapshots are written from the last mentor run of each local date. A rebuild regenerates every date that had a snapshot, "as of" that date, then today (D-059). `priority`/`status` are filled from Slice 5.

## 7. System

`audit_log(id, at UTC, entity_type, entity_id, action, payload_json)`. Every state-changing user action writes one:
- goal change;
- observation correction;
- story/project edit;
- manual suspend/resume and triage actions;
- plan regenerate, skip, defer;
- reflection;
- seed reload;
- rebuild.

## 8. Rules (formerly DATABASE_RULES.md)

1. **Never delete or update observations.** Corrections insert a superseding row. Projections ignore superseded rows.
2. **No soft-delete of evidence** because a skill or problem is retired. Retired catalog rows get `active = false`.
3. **Time:** instants are UTC `DATETIME`. Calendar facts are local `DATE`s in `app_settings.timezone`: `attempted_on`, `observed_on`, `occurred_on`, `due_date`, `plan_date`, `week_start`, `snapshot_date`. Engines use only local dates.
4. **Integers for scores, points, levels, minutes, basis points.** `DECIMAL` only for stored `quality`/`severity` display values. Never `FLOAT`/`DOUBLE`.
5. **Versioning:** every derived row carries `ruleset_version`; catalog rows carry `seed_version`; every mentor run records both.
6. **Rebuild:** `POST /admin/rebuild` truncates derived tables and replays catalog + activity + decisions. It must reproduce identical derived rows (deterministic replay test).
7. **Idempotency:** a daily plan is generated once per `plan_date` (UNIQUE). Repeated `GET /today` returns the frozen plan. Observation POSTs accept an optional `client_request_id` (UNIQUE when present) so double-submits are rejected.
8. **Backup:** nightly `mysqldump --single-transaction` compressed to `backups/`, 14-day retention (`scripts/backup.sh`, host cron). A restore test (`scripts/restore.sh` into a scratch DB + row-count check) must pass before Slice 4 is closed (real data exists from Slice 3).

## 9. Indexes (beyond PKs and UNIQUEs)

| Table | Index |
|---|---|
| all FKs | index on each FK column |
| `problem_attempts` | (problem_id, attempted_on), (attempted_on), (revision_item_key) |
| `assessments` | (observed_on), (kind, observed_on), (source_key), (revision_item_key) |
| `assessment_skills` | (skill_id) |
| `mock_round_skills` | (skill_id) |
| `mocks` | (occurred_on) |
| `evidence` | (ruleset_version, skill_id, observed_on) |
| `revision_items` | (state, due_date), (skill_id) |
| `gap_states` | (status, priority) |
| `plan_items` | (plan_id, status), (skill_id) |
| `revision_item_actions` | (item_key, action_on) |
| `audit_log` | (entity_type, entity_id), (at) |

## 10. Learning layer (migration `0012_learning`, D-083)

Catalog (written only by the seed loader, natural keys, `seed_version`):

| Table | Key | Columns |
|---|---|---|
| `learning_tracks` | `track_key` | title, summary, components_json, position |
| `learning_topics` | `topic_key` | track_id, title, summary, position |
| `learning_topic_skills` | (topic_id, skill_id) | position |
| `learning_content` | `content_key` | content_type (17 values), title, minutes, difficulty, stages_json, observation_kind, time_limit_seconds, problem_ids_json, body_json (validated), source_file, position, active (deactivated, never deleted) |
| `learning_content_skills` | (content_id, skill_id) | position (0 = primary) |

`problems.guide_json` (nullable): seed coaching metadata (summary paraphrase, pattern, time, space, hints, mistakes, prerequisites, relevance).

User state (exported with the decision history, imported after plan items, removed by `dev-reset`):

| Table | Columns |
|---|---|
| `learning_sessions` | skill_id, stage, status ACTIVE/COMPLETED/ABANDONED, plan_item_id, budget_minutes, start_score, start_level, outcome, seed_version, started_at, completed_at |
| `learning_session_steps` | session_id, position (unique per session), step_kind CONTENT/PROBLEM/REFLECTION, content_key, problem_id, title, minutes, status PENDING/DONE/SKIPPED, observation_type, observation_id, points, passed, reflection, completed_at |

Progress is not stored: it is derived from current assessments with `source_key = content:<key>`. Learning sessions never hold evidence; their steps link to the observation that does.

## 11. Speaking practice (migration `0013_speaking_practice`, D-087)

One additive, append-only user table, `speaking_practices`: `id`, `assessment_id` (FK to `assessments`, unique: one row per observation), `source` (`BROWSER`/`MANUAL`), `transcript` (text, NULL for MANUAL), `duration_seconds`, `word_count`, `filler_count`, `metrics_json`, `metrics_version`, `self_reflection`, `created_at`. Constraints: a BROWSER row requires a transcript and a MANUAL row forbids one; counts are non-negative. There is **no audio column**; the session and content are derivable through the assessment (`source_key`, `learning_session_steps.observation_id`), so they are not stored twice. The assessment remains the only evidence. The table is in `USER_TABLES`/`IMPORT_ORDER` (export, import, dev-reset order). Downgrade drops only this table.
