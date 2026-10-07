# Master Mentor — Implementation Plan (Spec v2)

This is the single build order. It absorbs the former `BUILD_ORDER.md`. Update the checkboxes when a slice is done.

## Execution rules

- One vertical slice at a time. Inside a slice, work in this order:
  1. migration;
  2. pure domain + unit tests;
  3. service;
  4. API + API tests;
  5. minimal UI;
  6. scenario tests;
  7. docs/tracker update.
- Before a slice, write a short note (in the PR or commit message) covering: objective, files, DB changes, tests, acceptance criteria.
- A slice is done only when its acceptance criteria pass, and backend tests, frontend tests, ruff, mypy, eslint and `alembic upgrade head` (on an empty DB) have actually been run.
- Engines are pure: no clock, no DB, no env. `as_of_date` and `ruleset` are always passed in.
- Build budget: 10 h/week. Estimates assume that.

## Slice 0 — Specification v2 ✅

- [x] Glossary, role profile, evidence, skill graph, gap, revision, mentor, mission library, readiness, 20 scenarios
- [x] Seed skeletons: skills, role profile, problems, roadmap, mission templates
- [x] PRD, context, roadmap, data model, API, UI, plan, decision log

## Slice 1 — Foundation ✅ (completed 2026-10-04)

- [x] `docker-compose.yml` (repo root): `mysql` (MySQL 8.4), `backend` (FastAPI, uvicorn), `frontend` (Vite dev). All published ports bound to `127.0.0.1`; MySQL volume + health check; backend waits for healthy MySQL (D-037).
- [x] Backend skeleton: `app/api`, `app/services`, `app/domain`, `app/models`, `app/repositories`, `app/schemas`, `app/infrastructure`, `app/config.py` (typed settings); SQLAlchemy 2 engine/session.
- [x] Alembic initialized; baseline migration `0001_baseline` with `app_settings`, `audit_log`, `mentor_runs`.
- [x] `app/domain/rulesets/v1.py`: every constant from the spec docs, with frozen fingerprints (`fingerprints.py`) and `tests/unit/test_ruleset_version.py` (D-041).
- [x] Clock: `app/domain/clock.py` (Clock protocol, `FixedClock`, `local_date`, `today_local`); `app/infrastructure/clock.py` `SystemClock` is the only real-clock reader (AST-enforced test) (D-041).
- [x] Error envelope + success envelope helpers; `GET /api/v1/health` (503 `DEPENDENCY_UNAVAILABLE` when the DB is down) (D-040).
- [x] Tooling: pytest, ruff, mypy (strict on `app.domain`), vitest, eslint (zero warnings), vue-tsc; `make check` runs all of them in containers.
- [x] Frontend skeleton: Vue 3 + Vite + TypeScript + Pinia + router with the 7 placeholder pages and a Status page; API client; error boundary + global error handling.

**Acceptance (verified 2026-10-04):**
- `docker compose up` → mysql, backend and frontend are healthy; `/api/v1/health` returns 200 from the host and via the frontend proxy.
- `alembic upgrade head` works on an empty DB (and a migration test re-verifies upgrade/downgrade on the `_test` DB in every `make check`).
- `make check` is green: 72 backend tests, 12 frontend tests.

**Carried forward:** none blocking. Notes: after editing `frontend/package.json`, run `make frontend-deps` (the `node_modules` volume does not refresh by itself).

## Slice 2 — Catalog & seed validator ✅ (completed 2026-10-04)

- [x] Migration `0002_catalog`: 11 catalog tables (`DATA_MODEL.md` §2) + `catalog_loads` (D-044).
- [x] Pure validator `app/domain/catalog/` (vocabulary, graph, validate, fingerprint, templates):
  - unique keys; known parents and prerequisites; no self-reference; acyclic with the cycle path reported; depth ≤ 6;
  - `min_score ∈ {30,45,60}` and ≤ prerequisite target; no T1–T3 → T4 dependency;
  - `gate ≤ target mean`; weights = 100; track minutes ≤ 600; weekday budgets = 600;
  - each skill in exactly one milestone; no prerequisite introduced in a later milestone of the same track;
  - templates resolve every (component, stage); problems have exactly one primary mapping;
  - closed vocabularies; no floats; one shared `seed_version`; lock check.
- [x] Seed versioning: `seed_version` + per-file content fingerprints, frozen per version in `seed/seed.lock.yaml` (D-044).
- [x] Seed loader (`make seed`): validate → abort before writes → one-transaction upsert by natural key; inserted/updated/unchanged/deactivated/deleted counts; `catalog_loads` + audit only when something changed (idempotent).
- [x] CLI `python -m app.cli.catalog validate|seed|lock|status`; Make targets `seed-validate`, `seed`, `seed-lock`, `seed-status`; `make dev` now seeds.
- [x] Catalog read API under `/api/v1/catalog` (D-046); `/health` reports the loaded `seed_version`.
- [x] Internal catalog verification page `/catalog` (not the final Skills page).

**Acceptance (verified 2026-10-04):** 133 skills, 134 prerequisites, 133 role targets, 18 milestones, 44 problems, 86 templates loaded; second load is a no-op; an invalid seed aborts with zero writes; `make check` green (141 backend, 16 frontend tests).

**Not done here (moved):** `POST /problems` (user problems) → capture slice.

> **Sequencing (decided 2026-10-04, D-049):** capture comes before the evidence engine, so real logging starts as early as possible. The authoritative order is Slice 1 Foundation → 2 Catalog → 3 Activity Capture → 4 Evidence + Skill State → 5 Gap Engine → 6 Revision → 7 Mentor / Daily Plan → 8 Readiness → 9 Dashboard / UI consolidation → 10 Mocks / Behavioral / System Design → 11 Weekly Review → 12 Hardening.

## Slice 3 — Activity Capture ✅ (completed 2026-10-04) → real logging starts

- [x] Migration `0003_activity`: `problem_attempts`, `attempt_mistakes` (DATA_MODEL §4). No derived columns.
- [x] Raw attempt capture with the Spec v2 vocabulary (Outcome `PASS/PARTIAL/FAIL`; mistake codes from EVIDENCE_MODEL §5.3; `self_rating_before/after` 1–5; `explanation_score` 0–10; `complexity_correct`; timer/limit; hints; solution viewed; pattern identified; follow-up; execution rubric).
- [x] Append-only corrections (`supersedes_id` + audit); the latest valid version is discoverable.
- [x] Personal problems (`POST /problems`, `seed_version = 'user'`, ids ≥ 1,000,000); the seed loader refuses to collide with them.
- [x] APIs: `/problems`, `/problems/{key}`, `/problem-attempts` (create, list with skill/problem/date filters, detail, corrections).
- [x] Log UI: problems list (search, difficulty, skill, source), problem detail with history, ≤ 60 s attempt form with timer.
- [x] No scoring of any kind: the only result of logging is "Attempt recorded."

**Acceptance (verified 2026-10-04):** manual scenarios A–D (API + headless browser where available), 179 backend / 23 frontend tests, `make check` green. **Still needed before relying on real data long-term:** backup (first item of Slice 4).

## Slice 4 — Evidence + Skill State (~2 weeks)

- [x] **Backup first:** `backup` compose sidecar (nightly, 14-day retention), `make backup`, `make backup-verify` (restore into a scratch DB, row counts + CHECKSUM TABLE), `make restore-live` (confirmation + safety backup) (D-054).
- [x] JSON + CSV export (`/export/json`, `/export/csv`, `make export`) with test-enforced table classification (D-057); developer reset `make dev-reset CONFIRM=RESET-PREP-DATA` (D-058).
- [x] Generic assessment capture (`POST /assessments`, corrections, self-assessment sweep) (D-055).
- [x] `app/domain/evidence/derive.py` (EVIDENCE_MODEL §5) and `app/domain/skills/state.py` (levels, quality, bands, reality cap, peak, confidence, effective score, labels); `app/domain/baseline/calibration.py`.
- [x] Migration `0004_evidence` (assessments, assessment_skills, evidence, skill_states, skill_daily_snapshots).
- [x] Mentor run on every write; write envelope with `effects.skill_deltas` (D-056); `/admin/rebuild` + replay tests (D-059); `/skills`, `/skills/{key}` (evidence trail), `/baseline`.
- [x] Scenario fixture builders; E1–E5 and the evidence-defined skill states of S01, S03, S05–S09, S17 pass. The other scenarios give skill states as inputs for later engines (BG fixture); they are asserted in Slices 5–10.
- [x] UI: Skills page + skill detail with evidence trail, Baseline page (sweep + battery assessment form), skill deltas after every save.

**Acceptance (verified 2026-10-04):** browser run against the dev stack (sweep → declared unknown 0/L0/LOW; SOLID raises nothing; B04/B05 quizzes and a B02 attempt complete battery items; deltas shown; still calibrating; evidence trail shows scoring vs non-scoring rows); export CLI; restore of all 23 tables verified; `make check` green.

## Slice 5 — Gap Engine (~1.5 weeks)

- [x] Goals (versioned; target date, weekday budgets) and settings APIs + Settings page (D-063).
- [x] `app/domain/readiness/components.py` (READINESS §3), `app/domain/profile/` (engine catalog view, goal rules), `app/domain/gaps/` (facts, engine §2–§10); migration `0005_goals_gaps`; `gap_states`; `/gaps`, `/gaps/{key}`; gap summary on `/skills`; `effects.gap_deltas` (D-064).
- [x] Golden harness `tests/golden/` over the real seed (F0/BG fixtures). G1–G3 and the gap/priority expectations of S01–S20 pass (S09 corrected by D-061; revision-dependent facts are inputs until Slice 6).
- [x] UI: Settings (profile + goal versions), Skills top gaps + gap column, skill-detail gap panel.

**Acceptance (verified 2026-10-04):** browser run (goal via Settings → BUILD 38.1 weeks; top gaps in engine rank order; gap panel with type → stage and reasons; `/gaps` phase + calibration); live-DB migration cycle; `make check` green.

## Slice 6 — Revision (~1 week)

- [x] `app/domain/revision/` (model, projection replay, transitions §5–§7, triage/auto-resume proposals §8, gap facts + G7 health §9); migration `0006_revision`; projection runs inside every mentor run and feeds the gap engine (D-066).
- [x] `/revisions` (buckets, backlog/cap), manual suspend/resume, review linking via `revision_item_key` with validation, `effects.revision_changes` (D-067). Triage *recording* happens in the plan-generating run (Slice 7).
- [x] Revision expectations of S03–S06, S08, S11 (corrected by D-065), S16, S20 pass; transition unit tests.
- [x] UI: Revision page (buckets, review via problem re-solve or inline assessment, suspend/resume).

**Acceptance (verified 2026-10-05):** browser run (due problem re-solved via the Revision link → +3 days; pattern review 80 → index 2; manual suspend/resume → due today); rebuild reproduces items with actions; live-DB migration cycle; `make check` green.

## Slice 7 — Mentor / Daily Plan (~2 weeks)

- [x] `app/domain/mentor/` (model, roadmap order, problem picker, practice minutes, planner: candidates/scores/track floors/sort/packing/follow-up/stop list, messages 1–21); migration `0007_plans`; plan-generating run with triage recording; `/today`, regenerate, start/complete/skip/defer, `/plan/{date}` (D-068–D-070).
- [x] Golden: plans + full message texts of S01–S20 (readiness given as the scenario states it; computed in Slice 8). S03/S06 exposed rule-4 contradiction (D-068).
- [x] UI: Today page (message, calibration, plan cards with mission view, log result via linked attempt/assessment, no-evidence, tomorrow, skip reasons, regenerate, top gaps, stop list).

**Acceptance (verified 2026-10-05):** browser run on the dev DB (calibration message, due revision completed via a linked attempt → schedule moved +14 d, skip with reason, regenerate keeps done/skipped and does not re-offer skipped work); API lifecycle tests incl. same-inputs → same plan and input hash; `make check` green.

## Slice 8 — Readiness (~1 week)

- [x] `app/domain/readiness/engine.py` G0–G9 (G6/G9 over mock round / final-simulation lists), states incl. STRONG sustain and `lapsed`, blockers per (gate, subject) with merged conditions; migration `0008_readiness`; snapshot per local date; `/readiness`, `/readiness/history`; mentor consumes readiness (D-071).
- [x] Golden: readiness of S01–S20 + the §9 worked example (18 tests).
- [x] UI: Progress page (headline "STATE — n blockers · limiting: X a/b", components, gates, history) and readiness line on Today.

**Acceptance (verified 2026-10-05):** browser (Progress headline never shows "% ready"; 10 gates; Today readiness line); API tests incl. rebuild reproduces snapshots; `make check` green.

## Slice 9 — Dashboard / UI consolidation (~1 week)

- [x] Today per UI_SPEC §3 (header, blockers, why, mission timer, effects panel, revision footer); Skills (component cards → group → skills, Roadmap tab); skill detail (downstream, milestone, revision items, focus preview); Log (kind switch, histories, corrections); status icon + text everywhere; 390 px + keyboard pass (D-072).
- [x] `/roadmap`, skill-detail extras, `effects.readiness_change`; tests (backend read models, frontend StatusBadge/EffectsPanel/correction/timer).

**Acceptance (verified 2026-10-05):** browser run (13 checks incl. timer, effects, component cards, roadmap, Log assessment + correction) and a 390 px sweep of 8 pages (no horizontal scroll); found and fixed 3 whitespace rendering bugs ("critical89", "created , due") and a form-unmount bug; `make check` green.

## Slice 10 — Mocks / Behavioral / System Design (~1.5 weeks)

- [x] Capture: SD/LLD/machine coding/story/project/pattern drill through the assessment form (Log page, multi-kind, component-checked); stories, projects, prompts (Settings, audited) (D-073).
- [x] Mocks with rounds and final simulations (migration `0009_mocks_content`); L7 evidence, mock-weakness pressure, MOCK_WEAKNESS items, G6/G9/STRONG inputs, mock/final-simulation candidates, Mocks page with summary; plan completion with MOCK.
- [x] All 20 scenarios: gap, revision, plan/message and readiness expectations pass against the real seed (79 golden tests), plus an end-to-end chain with computed readiness; API end-to-end mock test mirrors S17 through the DB.

**Acceptance (verified 2026-10-05):** browser (mock with SD weakness → L7 change + MOCKW item due +2 + G6 message; MOCKW on Revision page; story from Settings → STORY item); API tests (9 mock/content + MOCK plan completion); `make check` green.

## Slice 11 — Weekly Review (~0.5 week)

- [x] `app/domain/review/weekly.py` (metrics, next-week focus); migration `0010_weekly_reviews`; lazy generation for completed weeks, stored once; audited reflection; Progress page weekly-review panel (D-074).

**Acceptance (verified 2026-10-05):** browser (review of 2026-09-28..10-04 shown; reflection saved and persisted); API tests (lazy generation, stored once, 409 unfinished week, 422 non-Monday, audit); unit tests for metrics; `make check` green.

## Slice 12 — Hardening (~1 week)

- [x] Export v2 (`id_maps`) + import preview/validate/commit into an empty database (round trip reproduces every derived value), backup-age warning (D-075).
- [x] Replay audit (repeat / wall clock +5 years / reversed input order) and a 60-day synthetic history whose rebuild reproduces all 60 daily skill + readiness snapshots (D-076).
- [x] Domain purity AST test (no clock/random/uuid/time/os/I/O/float literals); security sweep (no v-html, no string-built SQL, all inputs `extra=forbid`, no secrets in the built bundle); index review with EXPLAIN on 9 hot queries; a11y + 390 px (Slice 9); dependency audit: `npm audit --omit=dev` 0 vulnerabilities, `pip-audit -r requirements.txt` no known vulnerabilities.
- [x] Final user journey through the real app and final audit report.

## UI/UX V2 redesign (after Slice 12)

- [x] Design system (tokens, semantic states, skeleton/empty/error), app shell (sidebar, tablet rail, phone bottom bar), focused navigation; developer tools under Settings → Developer (D-078).
- [x] Today (calibration hero, readiness, missions, gaps, mentor message, week, revision), mission card states, Prepare hub + area pages + DSA home, focused solving flow, Revise, skill detail, Roadmap, Mocks, Progress, Weekly review, Settings, Baseline, Log.
- [x] Read-only `GET /today/week` (+ unit and API tests); frontend tests 51 → 117 (fixtures typed against the API contract); axe-core audit 0 violations on every page at 1440 and 390; keyboard path verified; no horizontal overflow at 390 px; 1280×720, 1440×900, 1920×1080 and 390×844 screenshots reviewed; API calls per page de-duplicated and cached.

## Starting profile + calibration (after UI V2)

- [x] Migration `0011_starting_profile`; `/profile`, `/onboarding/complete`; self-report stored apart from evidence (tests prove scores, gaps and readiness are unchanged by it).
- [x] Calibration phase + effort (`/baseline`), personal roadmap and current state read models (pure domain + tests), declared-unknown labelling.
- [x] Onboarding wizard (first-run guard), calibration hub, calibration-first Today, personal roadmap, current state with self-report vs measured on Progress, edit from Settings.
- [x] Verified in a real browser as a brand-new user at 1280×720, 1440×900 and 390×844 (33 + 14 checks each, no console errors, no horizontal overflow); backend 474 tests, frontend 157 tests.


## MASTER_SPEC_V3 — learning layer (D-083 – D-085)

- [x] Phase A — repository audit and implementation map (`LEARNING_IMPLEMENTATION_BASELINE.md`); backup + restore verified before changes.
- [x] Phase B — learning domain (vocabulary, validation, grading, completion → observation, sessions, practice resolution, progress, coverage), migration `0012_learning`, seed loader, repository/service/API, vertical slice (lesson → check → evidence → skill state) with unit + API tests.
- [x] Phase C — skill page (why it matters, Learn/Practice/Test/Revise, A–D resolution, sessions), content page with runners, session page; "No problems match." dead end replaced.
- [x] Phase D — problem bank 44 → 137 with guides, derived practice state, DSA curriculum content.
- [x] Phase E — Python, DBMS/SQL, OS, networking/security, OOP content.
- [x] Phase F — LLD (10 case studies, 2 machine-coding exercises) and system design (fundamentals, distributed topics, 10 full designs).
- [x] Phase G — practical engineering scenarios and code reviews, 6 flagship projects with milestones and defense, behavioral STAR content; stories gain trade-offs.
- [x] Phase H — mock kits per loop round (no new round types).
- [x] Phase I/J — plan learning previews and "Start the session" on Today's missions; sessions close their plan item.
- [x] Phase K — coverage report (API + Developer page) and the no-required-gap test.
- [x] Phase L/M — UX hardening, browser validation, final audit (`FINAL_AUDIT.md`).

## 7. Communication & professional English track (D-087)

- [x] Seed-v3: 28 optional skills in 5 groups, T4 tiers, `COMM-1` milestone, `coding.comm_*` templates, curriculum track, 128 content items.
- [x] Migration `0013_speaking_practice` (additive), model, export/import registration.
- [x] Pure `domain/communication` (metrics, lexicon, cross-track picker, readiness view); speaking completion through the existing assessment path.
- [x] Optional cross-track step with plan closure independent of it; revision for `comm.*`; planner packing and stop-list rules; isolation from G8 and technical track minutes.
- [x] Communication Readiness, history, speaking runner with manual fallback, UI isolation.
- [x] Tests (backend, frontend), docs, browser validation, final audit (`FINAL_AUDIT.md` Part IV).
