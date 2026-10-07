# Master Mentor — API Specification (Spec v2)

Base path `/api/v1`. JSON only. The server binds to `127.0.0.1`; there is no auth in MVP (decision D-019). Every endpoint has one owner domain. Routers validate input and call one application service. Business rules live in domain engines.

## 1. Conventions

**Success envelope**

```json
{ "data": { }, "meta": { "as_of_date": "2026-11-02", "ruleset_version": "v1", "seed_version": "seed-v1", "run_id": 812 } }
```

`meta.run_id` is present on every response containing derived data. Lists use `data: [...]` plus `meta.count`.

**Write envelope** (every observation write): the response carries the effects of the synchronous mentor run.

```json
{ "data": { "observation": { } },
  "effects": {
    "skill_deltas":   [{ "skill_key": "graph.traversal", "before": {"score": 48, "effective": 41, "level": 3, "confidence": "MEDIUM"},
                                                         "after":  {"score": 51, "effective": 44, "level": 3, "confidence": "MEDIUM"} }],
    "gap_deltas":     [{ "skill_key": "graph.traversal", "before": {"priority": 60, "status": "CRITICAL"}, "after": {"priority": 57, "status": "HIGH"} }],
    "revision_changes": [{ "item_key": "PROBLEM:105", "change": "CREATED", "due_date": "2026-11-03" }],
    "readiness_change": { "before": "FOUNDATION", "after": "FOUNDATION", "blockers_added": [], "blockers_removed": [] } },
  "meta": { } }
```

**Error envelope**

```json
{ "error": { "code": "VALIDATION_ERROR", "message": "…", "details": {} } }
```

Error codes: `VALIDATION_ERROR` (422), `NOT_FOUND` (404), `METHOD_NOT_ALLOWED` (405), `CONFLICT` (409: duplicate `client_request_id`), `INVALID_STATE` (409: e.g. completing a DONE item), `DEPENDENCY_UNAVAILABLE` (503: database unreachable), `SEED_INVALID` (500 at startup), `INTERNAL` (500, never leaks internals). The client adds `NETWORK_ERROR` and `INVALID_RESPONSE` for transport failures (D-040).

**Dates:** request and response dates are local `YYYY-MM-DD`; instants are ISO-8601 UTC. `as_of_date` defaults to today in `app_settings.timezone`. It may be passed explicitly only on `/admin/*` and in tests.

## 2. Endpoints

### System and admin (domain: system)

| Method | Path | Purpose | Response `data` |
|---|---|---|---|
| GET | `/health` | liveness + DB connectivity (used by the Docker health check) | `{db: "ok", seed_version, ruleset_version}`; `seed_version` is `null` until the catalog is loaded (Slice 2); 503 `DEPENDENCY_UNAVAILABLE` if the DB is unreachable |
| POST | `/admin/rebuild` | truncate derived tables, replay everything | `{runs, snapshots_rebuilt, duration_ms}` |
| POST | `/admin/seed/reload` | validate and load `seed/*.yaml`, then rebuild | `{seed_version, changes}` |
| GET | `/export/json` | full export (all classes except derived) | file download |

### Settings and goal (domain: profile)

| Method | Path | Purpose |
|---|---|---|
| GET / PATCH | `/settings` | timezone, display name |
| GET | `/goals/active` | active goal with profile, phase, `weeks_left` |
| POST | `/goals` | create a goal version valid from today (closes the previous version; audited; triggers a run) |
| PATCH | `/goals/active` | change target date / weekday budgets / profile: inserts a new version valid from today (audited; triggers a run) |
| GET | `/goals/history` | all versions |

### Catalog (domain: catalog) — implemented in Slice 2

Static seed data under `/catalog` (D-046). Every response carries `meta.seed_version`; lists carry `meta.count`. 409 `INVALID_STATE` when no catalog is loaded.

| Method | Path | Returns |
|---|---|---|
| GET | `/catalog` | loaded version: `seed_version`, `catalog_fingerprint`, component versions (`catalog_version`, `skill_graph_version`, `role_profile_version`, `problem_catalog_version`, `mission_template_version`, `roadmap_version` = `seed_version+fingerprint[:12]`), file fingerprints, row counts, `loaded_at` |
| GET | `/catalog/skills?component=&group=&tier=` | active skills in seed order with tier, importance, target, floor, required |
| GET | `/catalog/skills/{key}` | detail: + prerequisites (with `min_score`), dependents, milestone, problem count, evidence kinds |
| GET | `/catalog/skills/{key}/prerequisites?transitive=` | direct (default) or transitive prerequisites with depth |
| GET | `/catalog/skills/{key}/dependents` | skills that list this one as a prerequisite |
| GET | `/catalog/tree` | components → groups → skill keys |
| GET | `/catalog/groups/{group_key}/skills` | children of a skill group |
| GET | `/catalog/role-profile?profile_key=` | active profile (single loaded profile until goals exist), config, tier counts, critical skills |
| GET | `/catalog/role-profile/targets?required=` | per-skill tier, importance, target, floor, required |
| GET | `/catalog/roadmap` | tracks → milestones → skills; baseline battery |
| GET | `/catalog/roadmap/milestones/{key}` | one milestone |
| GET | `/catalog/problems?skill=&difficulty=` | active problems with skill mappings |
| GET | `/catalog/problems/{id}` · `/catalog/problems/by-key/{platform}/{platform_key}` | one problem by stable id or stable key |
| GET | `/catalog/mission-templates?component=&stage=&skill=` | templates |
| GET | `/catalog/mission-templates/resolve?component=&stage=&skill=&gap_type=` | the template the mentor would use + lookup level 1–5; 404 `CONTENT_MISSING` |

The user-facing read models below (`/skills`, `/skills/{key}` with state and gap, `/roadmap` with completion) arrive with the engines and compose over the catalog. `POST /problems` (user problems, `seed_version = 'user'`) arrives with capture.

### Catalog-derived read models (later slices)

| Method | Path | Purpose |
|---|---|---|
| GET | `/skills?component=&group=&tier=&status=` | skill list with state + gap summary (Skills page) |
| GET | `/skills/{key}` | skill detail: state, gap (full §11 object), prerequisites with satisfaction, downstream, evidence timeline (last 50 rows), revision items, milestone, recommended focus + template |
| GET | `/problems?skill=&difficulty=&unseen=` | problem list with attempt counts |
| POST | `/problems` | add a user problem (`platform`, `platform_key`, title, difficulty, skills with exactly one primary) |
| GET | `/templates/{key}` | mission template (for the mission view) |
| GET | `/roadmap` | tracks, milestones, completion, current milestone per track, baseline battery progress |

### Activity capture (domain: activity) — implemented in Slice 3 (D-051)

| Method | Path | Purpose |
|---|---|---|
| GET | `/problems?q=&difficulty=&skill=&source=CATALOG\|PERSONAL` | active catalog + personal problems with `attempt_count` and `last_attempt` |
| GET | `/problems/{ref}` | `ref` = stable key `LEETCODE:two-sum` or numeric id |
| GET | `/problems/{ref}/attempts?include_superseded=` | that problem's history, chronological |
| POST | `/problems` | personal problem (`platform`, `platform_key`, `title`, `difficulty`, `url?`, `expected_minutes?`, `skills[{skill, mapping_weight_bp}]` with exactly one primary); 409 if the key exists |
| POST | `/problem-attempts` | record a raw attempt (body = `problem_attempts` fields, Spec v2 names; unknown fields → 422); 201 with the stored record only, no scores |
| GET | `/problem-attempts?skill=&problem=&from=&to=&outcome=&include_superseded=&order=asc\|desc&limit=&offset=` | newest first by default; `skill` adds `skill_mapping_bp`; `from`/`to` are local dates |
| GET | `/problem-attempts/{id}` | exactly what was entered, plus `supersedes_id`, `superseded_by_id`, `is_current` |
| POST | `/problem-attempts/{id}/corrections` | append a corrected version; 409 `INVALID_STATE` (with `latest_attempt_id`) if `{id}` was already corrected |

Audit actions: `CREATE_PROBLEM_ATTEMPT`, `CORRECT_PROBLEM_ATTEMPT`, `CREATE_PERSONAL_PROBLEM`. The write envelope with `effects` (below) arrives with the evidence engine in Slice 4.

### Evidence, skills and baseline — implemented in Slice 4 (D-055–D-060)

| Method | Path | Purpose |
|---|---|---|
| POST | `/problem-attempts`, `/problem-attempts/{id}/corrections` | now return the write envelope: `data` = stored record, `effects {run_id, skill_deltas}`, `meta {as_of_date, ruleset_version, seed_version, run_id}` (D-056); body also accepts `battery_item_key`, `revision_item_key` |
| POST | `/assessments` | `kind, observed_at?, mode, source_key, notes_used, reference_used, hints_used, timed, time_limit_seconds, time_seconds, peer_evaluated, applied, unseen_variant, difficulty, followup_points, communication_points, rubric, familiarity, study_minutes, skills[{skill, outcome_points, mapping_weight_bp, is_pattern_target}], self_rating_before/after, notes, revision_item_key, battery_item_key, client_request_id`; rules in D-055 |
| POST | `/assessments/self-assessment-sweep` | `{entries[{skill, familiarity}], observed_at?, client_request_id? (≤ 56, "-n" appended)}` → one SELF_ASSESSMENT per skill, `battery_item_key = M0-B01`, `source_key = battery:M0-B01` |
| GET | `/assessments?kind=&skill=&from=&to=&include_superseded=&limit=&offset=` · `/assessments/{id}` | history (newest first) / one record with `supersedes_id`, `superseded_by_id`, `is_current` |
| POST | `/assessments/{id}/corrections` | append a corrected version (409 `INVALID_STATE` + `latest_assessment_id` if already corrected); audited `CORRECT_ASSESSMENT` |
| GET | `/skills?component=&group=&tier=&label=` | catalog fields + `state {score, effective_score, level, confidence, label, peak_score, evidence_count, distinct_sources, last_practiced_on, last_observed_on, reality_capped, declared_unknown, assessed}`; meta has `run_id` |
| GET | `/skills/{key}` | + `prerequisites[{skill, min_score, effective_score, satisfied}]`, `evidence[]` (≤ 50, newest first, each flagged `considered` / `qualifying`) |
| GET | `/baseline` | battery items with `complete`, `next_item`, `required`, `assessed_required`, `assessed_pct`, `calibration_mode` |
| POST | `/admin/rebuild` | `{runs, snapshots_rebuilt, evidence_rows, duration_ms}`; audited `REBUILD_DERIVED` (D-059) |
| GET | `/export/json` · `/export/csv` | attachment: JSON document `{format, format_version, exported_at, seed_version, counts, tables}` / zip of CSVs + manifest (D-057) |

### Settings, goals, gaps — implemented in Slice 5 (D-063, D-064)

| Method | Path | Purpose |
|---|---|---|
| GET / PATCH | `/settings` | `{timezone, display_name}`; PATCH validates the IANA zone, is audited (`UPDATE_SETTINGS`) and returns the write envelope |
| GET | `/goals/active` | goal version valid today + `phase`, `weeks_left` (1 decimal); 404 if none |
| POST | `/goals` | `{target_date?, weekday_budgets? (7 ints, default profile), profile_key?}` → new version from today, closes the previous one; audited `CREATE_GOAL`; write envelope |
| PATCH | `/goals/active` | same fields + `clear_target_date`; omitted fields are copied; audited `CHANGE_GOAL`; write envelope |
| GET | `/goals/history` | every version, oldest first |
| GET | `/gaps?status=&component=&limit=` | `data = {phase, weeks_left, infeasible_components, calibration_mode, gaps[]}` (GAP_ENGINE §11 objects in rank order); `meta.count` = gaps returned |
| GET | `/gaps/{skill_key}` | one gap + `evidence {reason → [{source_type, source_id, observed_on, level, outcome_points, source_key}]}` |

Write envelopes now also carry `effects.gap_deltas[{skill_key, before{priority,status}, after}]`.

### Revision — implemented in Slice 6 (D-066, D-067)

| Method | Path | Purpose |
|---|---|---|
| GET | `/revisions?bucket=overdue\|due\|upcoming\|maintenance\|suspended\|graduated` | `data = {backlog_minutes, cap_minutes, triage_threshold_minutes, counts, items[{item_key, item_type, skill, skill_name, tier, importance, parked, state, suspend_reason, interval_index, due_date, days_overdue, lapses, needs_reinforcement, minutes, bucket, review_kind, subject_ref, last_reviewed_on}]}` |
| POST | `/revisions/{item_key}/suspend` · `/resume` | manual decision (action row + audit `SUSPEND_REVISION_ITEM` / `RESUME_REVISION_ITEM`), then a run; returns the item; 409 `INVALID_STATE` from the wrong state |

Reviews are ordinary writes (`POST /problem-attempts`, `POST /assessments`) with `revision_item_key`; `effects.revision_changes` reports the move.

### UX read models — implemented in Slice 9 (D-072)

| Method | Path | Purpose |
|---|---|---|
| GET | `/roadmap` | `{as_of_date, tracks[{track, current_milestone, milestones[{key, name, position, content, skills[{key, required, level, done}], required_total, required_done, extra_exit[{text, met}], complete, current}]}], baseline{done, total, next_item, calibration_mode}}` |
| GET | `/skills/{key}` | adds `dependents[]`, `milestone{key, name, track}`, `revision_items[]`, `focus{stage, template_key, minutes, pass_rule, observation_kind}` |
| GET | `/today` | `revisions` adds `backlog_minutes`, `cap_minutes` |

Write envelopes add `effects.readiness_change {before, after, blockers_added, blockers_removed}`.

### Mocks and content — implemented in Slice 10 (D-073)

| Method | Path | Purpose |
|---|---|---|
| POST | `/mocks` | `{occurred_at?, source, is_final_simulation, notes?, rounds[{round_type, duration_minutes, round_score, communication_points?, rubric?, skills[{skill, outcome_points, is_weakness}]}], client_request_id?}` → write envelope |
| GET | `/mocks?include_superseded=&limit=` · `/mocks/{id}` | history / one mock with rounds |
| POST | `/mocks/{id}/corrections` | superseding version; 409 with `latest_mock_id` if already corrected |
| GET | `/mocks/summary` | `{by_type[{round_type, rounds_60d, required_60d, non_self_60d, latest, trend, g6_failing}], g6_passed, repeated_weaknesses, final_simulations[{mock_id, date, source, valid, passed, failure}], g9_passed, g9_failing, simulation_eligible}` |
| GET / POST | `/stories` · PATCH `/stories/{id}` (fields, `archived`) | stories with competencies (behavioral skills; position 1 owns the revision item); audited |
| GET / POST | `/projects` · PATCH `/projects/{key}` | projects; audited |
| GET / POST | `/prompts?skill=` | assessment prompts; `source_key = prompt:<prompt_key>`; kind must fit the skill's component |

`POST /plan/items/{id}/complete` accepts `observation.type = MOCK`.

### Observations (domain: evidence capture) — original design (superseded by the implemented endpoints above)

All writes accept an optional `client_request_id`, `plan_item_id`, `revision_item_key` and `battery_item_key`. All writes return the write envelope.

| Method | Path | Body (key fields) |
|---|---|---|
| POST | `/attempts` | `problem_id, attempted_on, mode, outcome, seen_elsewhere, hints_used, solution_viewed, pattern_identified, timed, time_limit_seconds, time_seconds, explanation_score, complexity_correct, followup_solved, execution_rubric, mistakes[], self_rating_before, self_rating_after, notes` |
| POST | `/assessments` | `kind, observed_on, mode, source_key, conditions{…}, followup_points, communication_points, rubric, familiarity, study_minutes, skills[{skill_key, outcome_points, mapping_weight_bp, is_pattern_target}], self_rating_before, notes` |
| POST | `/assessments/self-assessment-sweep` | `[{skill_key, familiarity}]`: battery item B01, one assessment per skill |
| POST | `/mocks` | `occurred_on, source, is_final_simulation, rounds[{round_type, duration_minutes, round_score, rubric, skills[{skill_key, outcome_points, is_weakness}]}]` |
| POST | `/observations/{type}/{id}/correct` | full replacement body; inserts a superseding row; audited |
| GET | `/observations?from=&to=&skill=&type=` | history (Log page) |

Validation highlights:
- outcome enums;
- `0 ≤ points ≤ 100`; `0 ≤ explanation_score ≤ 10`; self-ratings 1–5;
- `time_seconds` is required when `timed`;
- `solution_viewed` implies the outcome cannot be a clean PASS for level purposes (accepted, level capped);
- assessment skills must exist and match the kind's allowed components;
- `familiarity` only on SELF_ASSESSMENT.

### Stories and projects (domain: content)

| Method | Path |
|---|---|
| GET / POST | `/stories` |
| PATCH | `/stories/{id}` (audited) |
| GET / POST | `/projects` |
| PATCH | `/projects/{id}` (audited) |
| GET / POST | `/prompts` (assessment prompts with answer keys) |

### Gaps (domain: gaps)

| Method | Path | Response |
|---|---|---|
| GET | `/gaps?status=&component=&limit=` | ranked gap objects (`GAP_ENGINE.md` §11) + `phase`, `weeks_left`, `infeasible_components` |
| GET | `/gaps/{skill_key}` | one gap with full metrics and the evidence rows that caused each reason code |

### Revision (domain: revision)

| Method | Path | Purpose |
|---|---|---|
| GET | `/revisions?bucket=overdue\|due\|upcoming\|suspended\|graduated` | items with minutes, days overdue, skill importance; meta: backlog, cap |
| POST | `/revisions/{item_key}/suspend` · `/resume` | manual action (audited) |

A review is recorded by posting an observation with `revision_item_key`. The write envelope reports the outcome and the new due date.

### Today and plan (domain: mentor) — implemented in Slice 7 (D-068–D-070)

`GET /today` returns `data = {plan_date, phase, weeks_left, goal_exists, calibration{active, assessed, required, assessed_pct, battery_done, battery_total, next_item}, readiness{state, weighted_score, limiting_component, blockers[≤3]}, top_gaps[≤3], revisions{due, overdue}, plan{id, plan_date, run_id, ruleset_version, budget_minutes, allocated_minutes, unallocated_minutes, done_minutes, phase, calibration_mode, regenerated_count, items[], stop_list[], dropped[], message{rule, text, payload}}}`. Items carry the mission view: `template{key, observation, pass_rule, output_level, next_on_pass}`, `problems[{id, key, title, difficulty, url}]`, `explanation`, `status`, links. `POST /plan/items/{id}/complete` returns the write envelope with `data = {item, observation}`.

#### Original design table

| Method | Path | Purpose |
|---|---|---|
| GET | `/today` | **The single read model for the Today page.** Generates and freezes the plan if absent. Returns: readiness `{state, blockers (top 3), limiting_component, weighted_score}`, `calibration {active, assessed, required, battery_progress}`, top 3 actionable assessed gaps, plan (`MENTOR_ENGINE.md` §11), stop list, message, due/overdue revision counts, phase, weeks_left. |
| GET | `/today/week` | **Read-only** week-to-date context for the Today page (D-078). Runs no engine and creates no plan. `data = {plan_date, week_start, week_end (Mon–Sun, local), preparation_day (days since the first goal version, or null), target_minutes (the active goal's weekly minutes, or null), practice_minutes (recorded practice Mon..today), active_days, minutes_by_track[{track, minutes, weekly_target}], revision{planned, done, completion_pct}}`. Minute attribution is the same as `summarize_practice` (recorded time split across skills); `revision` counts this week's non-discarded REVISION plan items. |
| POST | `/plan/today/regenerate` | explicit regenerate (keeps DONE/SKIPPED; audited) |
| POST | `/plan/items/{id}/start` | marks start time (for the client timer); no rule effect |
| POST | `/plan/items/{id}/complete` | `{observation: {type, body}}` or `{no_evidence: true}` → the observation is written + linked; returns the write envelope |

Baseline work recorded outside its plan item (D-082): when `POST /assessments/self-assessment-sweep`, or `POST /assessments` / `POST /problem-attempts` with a `battery_item_key`, succeeds and **today's** plan already holds a PENDING item for that battery item, the observation is linked to it (`plan_item_id`; for the sweep, every row, with the item pointing at the first) and the item becomes DONE through the same completion step as `/plan/items/{id}/complete` (one `COMPLETE_PLAN_ITEM` audit row). No plan is created, and SKIPPED, DEFERRED or DONE items are left as they are. Corrections and imports never touch plan items.

| POST | `/plan/items/{id}/skip` | `{skip_reason}` |
| POST | `/plan/items/{id}/defer` | — |
| GET | `/plan/{date}` | historical plan (read-only) |

### Readiness (domain: readiness) — implemented in Slice 8 (D-071)

`GET /readiness` → the §10 object of today's snapshot (`state, simulation_eligible, lapsed, weighted_score, limiting_component, components[], gates[{gate, passed, failing}], blockers[{gate, subject, kind, actual, required, deficit, message, skills}], all_failing[]`). `GET /readiness/history?from=&to=` → `[{date, state, weighted_score, limiting_component, components{key: score}, blockers}]` (default: last 90 days).

#### Original design table

| Method | Path | Response |
|---|---|---|
| GET | `/readiness` | full object (`READINESS_MODEL.md` §10) |
| GET | `/readiness/history?from=&to=` | daily snapshots (state, weighted, components) |

### Weekly review (domain: review) — implemented in Slice 11 (D-074)

`GET /weekly-reviews` (newest first) · `GET /weekly-reviews/latest` · `GET /weekly-reviews/{monday}` (422 if not a Monday, 409 if the week has not ended) → `{id, week_start, run_id, ruleset_version, metrics{week_start, week_end, active_days, planned_minutes, completed_minutes, plan_completion_pct, revision_completion_pct, minutes_by_track, top_gaps, gap_changes, strongest_improvement, biggest_regression, readiness{start, end, new_blockers, cleared_blockers}, mocks, backlog_minutes}, next_focus{top_gaps, tracks_below_floor, stop_list}, reflection, generated_at, reflected_at}`. `POST /weekly-reviews/{monday}/reflection` `{improved, still_weak, failure_causes, stop_doing, next_priority}` (audited).

#### Original design table

| Method | Path | Purpose |
|---|---|---|
| GET | `/weekly-reviews/latest` | generates the last completed week's review if missing |
| GET | `/weekly-reviews/{week_start}` | |
| POST | `/weekly-reviews/{week_start}/reflection` | `{improved, still_weak, failure_causes, stop_doing, next_priority}` (audited) |

### Data safety — implemented in Slice 12 (D-075)

| Method | Path | Purpose |
|---|---|---|
| POST | `/import/preview` | body = a JSON export (format v2) → `{ok, errors, warnings, counts, export_seed_version, loaded_seed_version, exported_at, confirmation}`; writes nothing |
| POST | `/import/commit` | `{document, confirm: "IMPORT-INTO-EMPTY-DATABASE"}` → `{inserted{table: rows}, rebuild}`; 422 when invalid or the database already has preparation data |
| GET | `/system/backup-status` | `{available, latest_file, taken_at, age_hours, warning, max_age_hours, message}` |

## 3. Removed from v1

| v1 endpoint | Reason |
|---|---|
| `/auth/*` | single user on localhost (D-019) |
| `/dashboard` | replaced by `/today` + `/readiness/history` |
| `/revisions/due`, `/revisions/overdue`, `/revisions/{id}/complete` | one bucketed list; reviews are observations |
| `/daily-plan/generate` | `/today` generates lazily; regenerate is explicit |
| `/gaps/top` | `/gaps?limit=3` |
| `/mocks/{id}/scores` | rounds are posted with the mock |
| `/import/*`, `/system/backup-status` | out of MVP (restore = dump restore; backfill = script). `/export/csv` was reinstated in Slice 4 (D-057); import is planned for Slice 12. |

## 4. Testability

- Every endpoint has API tests.
- Every derived response is reproducible from DB state through `/admin/rebuild`; the deterministic replay test compares results before and after.
- Golden scenarios run at the service layer with an injected `as_of_date`.

## Starting profile, calibration status, personal roadmap and current state (D-080)

| Method | Path | Notes |
|---|---|---|
| GET | `/profile` | `{display_name, timezone, onboarding{completed, completed_at}, experience{years, current_role, previous_role}, technologies[], company_profile, self_report{strengths, weaknesses, never_studied, recently_studied}, target{role{profile_key, name, seniority}, target_date, weekday_budgets, weekly_minutes, phase, weeks_left} \| null, available_roles[]}` |
| PUT | `/profile` | Patch of the context fields (`extra=forbid`): `display_name`, `experience`, `technologies` (≤ 30 × 40 chars, de-duplicated case-insensitively), `company_profile`, `self_report` (skill-group keys that must exist; strengths ⊥ weaknesses, strengths ⊥ never_studied, never_studied ⊥ recently_studied). Audited. Changes no score. |
| POST | `/onboarding/complete` | Profile fields + `goal{target_date, weekday_budgets, profile_key}`. The goal is validated first (nothing is half-saved), a new goal version is written only when a goal changes, the first-run flag is set once; then a `GOAL` mentor run. Write envelope. |
| GET | `/baseline` | Adds `phase` (`NOT_STARTED` / `IN_PROGRESS` / `ENOUGH_MEASURED` / `COMPLETE`), `personalization_threshold_pct`, `minutes_total`, `minutes_done`, `minutes_remaining`, `typical_daily_minutes` (average non-zero weekday budget), `estimated_days` (remaining ÷ typical, rounded up; a rough guide, the mentor schedules each day). |
| GET | `/roadmap/personal` | Read-only (two engine evaluations: today and the previous day). `{as_of_date, calibration_phase, available, based_on{role, target_date, weeks_left, phase, measured_skills, required_skills, blocked_skills, overdue_reviews}, focus_now[≤ 5], sections{build, consolidate, sharpen, maintain, parked, unmeasured, later: {count, items[≤ 8]}}, why[≤ 3]{…metrics, prerequisites}, changes{since, changed, entered[], left[]}}`. Items carry score, target, status, reason codes, `declared_unknown`, unsatisfied prerequisites and `next_step_minutes` from the mission library. `changes` is empty when nothing was in focus before. |
| GET | `/profile/state` | Read-only. `{counts, strong, developing, critical, unknown: {count, items[≤ 8]}, self_reported[{group_key, name, component, claims[], measured, total, skills[{score, target, confidence, status, declared_unknown}]}]}`. `measured` counts task evidence only; a "new to me" self-rating is listed with `declared_unknown = true`. |

## 11. Learning layer (D-083, LEARNING_ENGINE.md)

Read models carry what the UI needs to explain the current state, the recommendation, the reason and the evidence change; nothing is computed in the browser. Completions and session steps that record an observation return the write envelope (`effects` of the mentor run).

| Method | Path | Notes |
|---|---|---|
| GET | `/learning/curriculum` | tracks → topics → skills with score/target, gap status, content counts, done counts, coverage state |
| GET | `/learning/tracks/{track}` | the same for one track plus `content{topic_key: ContentSummary[]}` in seed order |
| GET | `/learning/content/{key}` | the item: type, minutes, difficulty, stages, observation kind, time limit, body (choice answers and explanations removed until graded; short answers keep their model answer), rubric, pass points, problems (with practice state), topic, the learner's progress |
| POST | `/learning/content/{key}/complete` | `{answers{qid:[idx]}, self_grades{qid\|card:0-2}, ratings{criterion:0-2}, followups{i:0-2}, minutes?, notes_used, reference_used, hints_used, timed, time_seconds?, milestone?, defense, notes?, client_request_id?}` → `{content_key, points, passed, followup_points, questions[{id, earned, chosen, answer, explanation, model_answer}], observation, progress}`; 201; guided/timed problems → 409 (recorded on the problem page) |
| GET | `/skills/{skill}/learning` | why it matters (tier label, target, rounds, unlocks, topic), state (score, label, confidence, gap status/type/focus), tabs `learn/practice/test/revision`, practice resolution `{case DIRECT\|RELATED\|CONCEPT\|UNCOVERED, direct[], related[{problem, via_skill, via_name, relation}], fallback_skill, fallback_relation}`, related skills, `next_action{kind START_SESSION\|RESUME_SESSION\|FALLBACK\|NONE, stage, reason, steps[], session_id, fallback_skill}`, coverage state |
| POST | `/learning/sessions` | `{skill, stage?, plan_item_id?, budget_minutes?}` → the new session, or the active one for that skill or plan item (resume); 409 `NO_CONTENT` when nothing fits the stage |
| GET | `/learning/sessions?status=` · `/learning/sessions/{id}` | session with steps, next position, outcome, `before{score, level}`, `after{score, level}` |
| POST | `/learning/sessions/{id}/steps/{pos}/complete` | CONTENT `{completion}`, PROBLEM `{attempt}` (a ProblemAttemptInput for the step's problem), REFLECTION `{reflection}` → `{session, completion, attempt_id}`; 409 when the session is finished or the step is not pending |
| POST | `/learning/sessions/{id}/steps/{pos}/skip` · `/learning/sessions/{id}/abandon` | audited |
| GET | `/learning/coverage` | `{summary{all, required}{FULL, PARTIAL, UNMEASURED, CONTENT_GAP}, content_counts{type: n}, rows[]}` (Developer / System) |
| GET | `/learning/mock-kits` | per loop round: `{round, round_type, minutes, components, focus_skills[], items[]}` |

Additions to existing read models: `GET /problems` and `/problems/{ref}` add `practice_state` (derived) and `guide` (seed coaching metadata), and a LeetCode URL when none is stored; `GET /today` / `GET /plan/{date}` add `plan.learning{item_id: {stage, minutes, steps[], session_id}}` for pending skill missions (derived, never part of the frozen items).

## 12. Communication (D-087)

- `POST /learning/content/{key}/complete` and the session step `complete` accept `completion.speech`: `{source: "BROWSER"|"MANUAL", transcript?: string (<= 8000), duration_seconds: 0..3600, reflection?: string}`. Unknown fields (for example client-sent metrics) are rejected with 422. BROWSER needs a transcript of at least 5 words and a plausible duration; MANUAL must not send one. The response adds `speaking` (server-computed signals, `criteria`, `metrics_version`, `evidence_note`). A repeated `client_request_id` returns 409 and records nothing.
- `POST /communication/preview` `{content_key, transcript, duration_seconds}` measures a transcript without storing anything.
- `GET /communication/readiness` returns six areas (status, summary sentence, evidence counts split measured / manual / other, per-skill rows) and a note that it is not part of Overall Readiness.
- `GET /communication/history?limit=` returns recent speaking practices (counts only, no transcript).
- Session and plan-preview steps carry `optional: boolean` (the cross-track prompt).
