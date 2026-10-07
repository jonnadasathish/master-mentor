# Master Mentor — Final Audit (Slices 1–12)

Date: 2026-10-05 · ruleset `v1` · catalog `seed-v1` · schema head `0010_weekly_reviews`.

This audit lists what was verified, how, and what is still limited. Every "pass" below comes from a command or test that was actually run; nothing here claims the system is free of defects.

## 1. Requirement traceability (PRD §5)

| Req | What | Implementation | Tests | Verification evidence |
|---|---|---|---|---|
| FR-1 | Goal (profile, target date, weekday budgets) | `services/profile_service.py`, `/goals*`, Settings page | `tests/api/test_gaps_api.py` (versions, validation) | browser Slice 5; final journey step 1 |
| FR-2 | Baseline battery + familiarity sweep, declared unknowns | `domain/baseline/calibration.py`, `/assessments/self-assessment-sweep`, `/baseline`, Baseline page | `test_calibration.py`, `test_evidence_api.py` (sweep), golden S01 | browser Slice 4; journey step 2 |
| FR-3 | Problem attempts (all fields, timer, backdate) | `services/activity_service.py`, AttemptForm | `test_activity_api.py`, `test_activity_rules.py`, `attemptForm.spec.ts` | journey step 3: logged through the plan in 0.4 s of form time (≤ 30 s target) |
| FR-4 | Assessments of every kind with per-skill points | `services/assessment_service.py`, `domain/activity/rules.py`, Log page | `test_evidence_api.py`, `test_evidence_derivation.py` | journey step 4 |
| FR-5 | Mocks with rounds, outcomes, weaknesses, source; final simulations | `services/mock_service.py`, Mocks page | `test_mocks_content_api.py` | browser Slice 10; journey step 5 |
| FR-6 | Stories (many competencies) and projects | `services/content_service.py`, Settings | `test_mocks_content_api.py` | browser Slice 10 |
| FR-7 | Corrections by superseding (append-only + audit) | attempts / assessments / mocks `/corrections` | activity, evidence and mock API tests | browser Slice 9 (Log correction) |
| FR-8 | Evidence + skill state after every write | `domain/evidence/derive.py`, `domain/skills/state.py`, `services/mentor_service.py` | `test_skill_state.py`, `test_evidence_derivation.py`, write-effects tests | effects panel in every browser slice |
| FR-9 | Ranked gaps with type, reasons, blockers, parking, focus | `domain/gaps/*` | golden `test_gap_scenarios.py` (S01–S20, G2, G3), `test_gaps_api.py` | browser Slice 5 |
| FR-10 | Revision items, PASS/PARTIAL/FAIL, leech, triage | `domain/revision/*` | golden `test_revision_scenarios.py`, `test_revision_engine.py`, `test_revisions_api.py` | browser Slice 6; journey step 6 |
| FR-11 | One frozen plan within budget, stop list, one message | `domain/mentor/*`, `services/plan_service.py` | golden `test_plan_scenarios.py` (all 20 plans + full message texts), `test_today_api.py` | browser Slices 7 and 9 |
| FR-12 | Complete / skip / defer; completion returns deltas | `services/plan_service.py`, Today page | `test_today_api.py`, `today.spec.ts` | journey step 3 (effects panel) |
| FR-13 | Readiness state, gates, blockers, daily snapshots | `domain/readiness/*` | golden `test_readiness_scenarios.py`, `test_readiness_api.py` | browser Slice 8; journey step 8 |
| FR-14 | Weekly review + reflection | `domain/review/weekly.py`, `services/review_service.py` | `test_weekly_review.py`, `test_reviews_api.py` | browser Slice 11 |
| FR-15 | Rebuild all derived state | `MentorService.rebuild`, `/admin/rebuild` | `test_replay_audit.py` (60-day history), rebuild API tests | journey step 10 |
| FR-16 | `ruleset_version` / `seed_version` on derived rows | models + migrations | `test_ruleset_version.py`, `test_seed_fingerprint.py` | schema test `test_schema_matches_models_exactly` |
| FR-17 | JSON export | `services/export_service.py`, `/export/json`, `make export` | `test_evidence_api.py`, `test_import_api.py` (round trip) | journey step 9 |
| FR-18 | Nightly dump, 14-day retention, tested restore | `backup` service, `scripts/backup-*.sh`, `restore-verify.sh` | — (infrastructure) | `make backup-verify` after every schema slice: "RESTORE VERIFIED", 38/38 tables, counts + checksums |
| FR-19 | CSV export + import (D-057, D-075); backup-age warning | `export_service.py`, `import_service.py`, `backup_status.py` | `test_import_api.py`, `test_backup_status.py`, `data.spec.ts` | round trip reproduces every derived value |

## 2. Golden scenarios

All 20 scenarios of `docs/domain/SCENARIOS.md` are asserted against the real `seed-v1` catalog:

- gaps and priorities;
- revision state;
- the full daily plan;
- the exact mentor message text;
- readiness state and blockers.

`tests/golden/test_end_to_end.py` also feeds the mentor computed (not given) readiness for S01, S02, S10, S12, S15, S18 and S20.

The tests found three contradictions in the spec. Each was fixed in the spec first:
- **D-061:** S09 FAILURE pressure;
- **D-065:** S11 problem #22 is EASY in the seed;
- **D-068:** mentor rule 4 against S03/S06.

## 3. Determinism (replay) audit

| Check | Test | Result |
|---|---|---|
| Same inputs, repeated | `test_replay_audit.py` (×4 runs), unit replay tests | identical |
| Wall clock moved 5 years, same `as_of_date` | `test_replay_audit.py`, `test_mentor_runs.py` | identical outputs and `input_hash` |
| Input order reversed (re-inserted) | `test_replay_audit.py` | identical skill states, gaps, revision items, readiness, plan, message. `input_hash` differs by design: it covers the stored surrogate ids (D-076) |
| 60-day history, rebuild | `test_sixty_day_history_rebuilds_every_daily_snapshot` | all 60 daily skill and readiness snapshots reproduced |
| Shuffled inputs inside engines | evidence, skill-state, gap, revision unit tests | identical |
| Export → wipe → import | `test_round_trip_reproduces_all_derived_state` | identical |

## 4. Formula / nondeterminism audit

- `tests/unit/test_domain_purity.py` (AST) checks that `app/domain` has:
  - no imports of `random`, `secrets`, `uuid`, `time`, `os`, `socket`, `requests`, `httpx`, `sqlalchemy` or `pathlib`;
  - no `open` / `print` / `eval` / `exec`;
  - no `datetime.now`, `utcnow` or `today`, and no `date.today`;
  - no float literals.
  
  It passes. A grep confirmed the same.
- Integer math is used throughout, with `Decimal` intermediates and a single `ROUND_HALF_UP` (`skills/state.py`).
- Ruleset constants are frozen by fingerprint (`rulesets/fingerprints.py`, `test_ruleset_version.py`).
- `wall-clock` reads exist only in `infrastructure/clock.py`, and in the services' `duration_ms` and `run_at` metadata, which is excluded from every comparison.

## 5. Security and data safety

- **Network and auth:** localhost-only ports; no authentication by design (D-019). There is no secret in the frontend bundle: a built bundle was checked for DB password values and markers.
- **Input and rendering:** all inputs are validated by Pydantic with `extra="forbid"`; SQL is ORM or bound parameters only; there is no `v-html`.
- **Destructive actions need typed confirmations:**
  - `make dev-reset CONFIRM=RESET-PREP-DATA` (backup first; development only);
  - `make restore-live CONFIRM=RESTORE-LIVE-DATABASE` (safety backup first);
  - import commit (`IMPORT-INTO-EMPTY-DATABASE`; empty databases only).
- **History:** observations are append-only; every state-changing action writes `audit_log`.
- **Dependencies:** `npm audit --omit=dev` found 0 vulnerabilities; `pip-audit -r requirements.txt` found no known vulnerabilities (2026-10-05).

## 6. Final user journey (real app, dev stack, after `make dev-reset`)

14/14 checks passed. The first run of step 3c read the card before the page reload finished; the API showed the item DONE, and a re-check of the UI confirmed it.

1. Goal.
2. Familiarity sweep.
3. Today in calibration:
   - (a) the plan contains battery item M0-B02;
   - (b) it was completed through the plan with a linked attempt and the effects panel shown;
   - (c) the plan item is DONE.
4. Assessment from Log.
5. Mock with a MOCKW item.
6. Revision items created automatically.
7. Skill evidence trail.
8. Readiness honestly NOT_MEASURED; weekly review shown.
9. JSON export.
10. Rebuild gives identical skill states and gaps.

## 7. Known limitations

- Readiness can reach INTERVIEW_READY only with recorded mocks and final simulations (by design).
- Feasibility uses the profile's track minutes, not the goal's weekday budgets (D-064).
- Practice minutes count only recorded time. An observation without a time and without a plan item counts 0.
- The template time-limit cap for assessment L4 is not applied to free (non-plan) assessments (D-055d).
- Import accepts only an empty database (no merge).
- STRONG and `lapsed` depend on stored daily snapshots, which exist only for days with a mentor run.
- The UI is desktop-first. Every page fits 390 px, but phone use was checked for layout and keyboard only.
- No commits were made: the repository root is the home directory (unchanged from Slice 1).

## 8. Final verification run (2026-10-05)

| Command | Result |
|---|---|
| `./scripts/make-in-docker.sh check` | exit 0: ruff "All checks passed!", mypy "no issues found in 132 source files", vue-tsc + eslint clean, **pytest 418 passed** (208 s), **vitest 51 passed** (15 files) |
| `./scripts/make-in-docker.sh backup-verify` | exit 0: "RESTORE VERIFIED: mastermentor-20261005T050139Z.sql.gz", tables restored = 38, live = 38, row counts and checksums equal |
| `alembic upgrade head` on an empty DB | covered by `tests/db/test_migrations.py` (8 passed): from-empty upgrade, model/schema diff = [], downgrade −1 / base and upgrade again |

## 9. Post-audit fix: backup visibility (D-077)

After this audit, the app showed "No backup found" although backups were verified. The cause was a stale backend container that predated its `./backups:/backups:ro` mount. The fix was to recreate the stack. `tests/api/test_backup_status_api.py` and `make backup-status-check` now cover this case.

---

# Part II — Learning layer audit (MASTER_SPEC_V3, D-078 – D-085)

Date: 2026-10-06 · ruleset `v1` · catalog `seed-v2` (catalog fingerprint `47b81e616a2a…`, locked in `seed/seed.lock.yaml`) · schema head `0012_learning`.

Every "pass" below comes from a command or test that was actually run in this session. Nothing here claims guaranteed hiring, a guaranteed interview or a guaranteed offer: the system maximises evidence-based readiness and says "not ready" until gates prove otherwise.

## A. What was already complete (verified, not rebuilt)

The 12 implementation slices; the evidence, skill-state, gap, revision, mentor, readiness, roadmap and calibration engines; baseline battery; starting profile; Today and UI/UX V2; D-079 (empty mentor-message clause), D-080 (starting profile + calibration), D-081 (Continue Calibration) and D-082 (battery work closes its plan item); backup and restore. Baseline verified before any change: backup + `RESTORE VERIFIED` (39 tables), then 478 backend / 165 frontend tests (previous `make check`).

## B. What was newly implemented

| Area | Delivered |
|---|---|
| Content model | 17 content types with stable keys, mapped to canonical skills; `seed/learning/` (curriculum + 57 content files), validated before import (`catalog validate`, `validate --draft [--only]` for authors) |
| Completion → evidence | reading → STUDY_SESSION; checks/quiz/cards → RECALL_QUIZ (server-graded); rubric practice → its kind with `outcome_points` and `followup_points`; project milestones → APPLIED_TASK, defense → PROJECT_WALKTHROUGH; problems → ordinary attempts. No evidence rule changed. |
| Sessions | pure slot composition per mentor stage, ≤ 7 steps, resume, skip, abandon, before/after score, closes the plan item (D-082 path), audited |
| Dead-end rule | practice resolution DIRECT / CONCEPT / RELATED / UNCOVERED; "No problems match." replaced by related practice, concept practice or an honest content gap |
| Problem bank | 44 → 137 curated problems (ids 1–44 unchanged), `guide` on every problem, derived practice state (not_started … interview_grade) |
| UI | skill page (why it matters, Learn/Practice/Test/Revise, session start), content page + 9 runners, session page, learning path on every Prepare area, Python / Practical engineering / Projects pages, problem guide + hint ladder, mock kits, Today mission session preview, coverage page (Settings → Developer) |
| Behavioral | stories gain a trade-offs field (all seven parts: Situation, Task, Action, Result, Metrics, Trade-offs, Reflection) |
| Docs | `LEARNING_ENGINE.md`, `CONTENT_AUTHORING_GUIDE.md`, `LEARNING_IMPLEMENTATION_BASELINE.md`, API_SPEC §11, DATA_MODEL §10, UI_SPEC §9, GLOSSARY, EVIDENCE_MODEL note, PROJECT_CONTEXT, ROADMAP §6, IMPLEMENTATION_PLAN, DECISION_LOG D-083–D-085 |

## C. Current learning engine, content and coverage

| Measure | Value |
|---|---|
| Tracks / topics | 8 / 72 (dsa, python, cs, lld, system_design, engineering, projects, behavioral) |
| Content items | **847** in 57 files: lesson 144, concept 8, worked example 30, visual 23, concept check 141, quiz 3, recall-card sets 142, coding exercise 53, SQL exercise 5, debugging scenario 33, design exercise 12, architecture case 23, interview question 104, behavioral question 30, guided problem 42, timed problem 48, project 6 |
| Skill coverage | **133 / 133 skills FULL** (lesson + concept check + practice + timed practice + recall cards); **123 / 123 required skills FULL**; 0 PARTIAL, 0 UNMEASURED, 0 CONTENT_GAP. A unit test fails if any required skill regresses. |
| Practice coverage | 137 problems with guides; every DSA pattern skill has ≥ 3 primary problems (≥ 1 guided and ≥ 1 timed suitable); 90 guided/timed problem steps; every skill has at least one practice item with a time limit |
| Mock coverage | every round of the existing loop (DSA ×2, CS, LLD, System design, Behavioral, Project deep dive) has a kit of timed prompts, one per skill, ordered by gap rank; no new round types, readiness unchanged |
| Project coverage | 6 flagship projects (Inventory Management System with the full Vue / FastAPI / MySQL / Redis / Docker / AWS / auth / CI-CD stack, URL Shortener, Notification Platform, Job Queue, Payment/Order, Social Feed) with requirements, architecture, schema, APIs, 5–10 milestones with rubrics, testing, deployment, observability, failure scenarios and defense questions |
| Behavioral coverage | 12 behavioral/communication skills, 30 timed (3-minute) behavioral questions with deterministic follow-ups, worked STAR stories with all seven parts |
| LLD / System design | 10 LLD case studies + 2 × 90-minute machine-coding exercises; 10 full system designs (45-minute limit) with the 11-criterion rubric |

## D. Verification (this session)

| Check | Result |
|---|---|
| `./scripts/make-in-docker.sh check` (literal `make check`, final run) | **exit 0: ruff "All checks passed!", mypy "no issues found in 152 source files", vue-tsc + eslint clean, pytest 523 passed (345 s), vitest 180 passed (23 files)** |
| Backend tests (earlier run on a private test DB, because another session shared the default one) | 522 passed |
| Frontend tests (vitest) | **180 passed** (23 files; 51 → 180 across the V2/V3 work) |
| ruff / ruff format / mypy (152 files) / vue-tsc / eslint | clean |
| Migrations | `0012_learning` is additive; tests: from-empty upgrade, model/schema diff = [], downgrade −1 and base, re-upgrade |
| Seed | `catalog validate` → "Seed valid: seed-v2"; seed loader test proves idempotent reload, retirement of a skill (incl. its problems and content) and stable ids |
| Domain purity | AST test still passes (`domain/learning` has no I/O, clock or float) |
| Golden scenarios | unchanged and passing: the harness is pinned to the original problems 1–44 so the bank growth only changes which problem a picker chooses, never a rule (D-084) |
| Browser (real Chromium, throwaway DB, brand-new user through onboarding, 33/33 + 44/44 checks per size) | **1280×720, 1440×900, 1920×1080, 390×844 all pass**; no console errors; no horizontal overflow on any learning page; the 44 checks cover skill page → session → check graded with explanations → summary with before → after; problem fallback; problem guide; all 8 Prepare areas; lesson, visual, project milestone, architecture case; mocks kits; coverage page; Today |
| Accessibility (axe-core, WCAG 2 A/AA + best practice) | 13 learning pages at 1440 and 390 px; one heading-order finding on the project page was fixed; re-audit 0 violations |
| Real database | backup + restore verified before (`RESTORE VERIFIED`, 39 tables) and after (46 tables) migrating; user data intact (123 assessments, 2 attempts, 4 goal versions, 6 revision items, 133 skill states); `GET /learning/coverage` on the real app: 123 required FULL, 847 items |

Defects found by the real-browser run and fixed: problem links used a stripped key (`binary-search` instead of `LEETCODE:binary-search`); the skill page printed a raw list as the observation kind; the project page skipped a heading level; a session picked another skill's lesson over the skill's own (primary-skill content is now preferred). Each has a test.

## E. Database and seed

| Item | State |
|---|---|
| Migrations | `0011_starting_profile` → `0012_learning` (7 learning tables, `problems.guide_json`, `behavioral_stories.tradeoffs`). Applied to the real database after a verified backup. |
| Seed | `seed-v2` loaded: 93 new problems, 44 problems updated with guides, 8 tracks, 72 topics, 847 content items; `seed-v1` remains frozen in the lock |
| Skill ids and history | unchanged (skills updated in place, 0 inserted/deactivated); no evidence row was rewritten |
| Backup/restore | `make backup` and `make backup-verify` pass before and after; export/import/reset classify the new tables |

## F. Known limitations

- **Content is authored, not field-tested.** It was written to a strict quality bar and machine-validated for structure, but facts that depend on versions or engines (InnoDB, PostgreSQL, CPython, Linux, cloud defaults) were flagged by the authors for human review; a sample of 14 graded questions was checked and all keys were correct. Treat the library as a strong first edition and correct what you find.
- **Self-graded rubrics are honest only if the learner is.** Practice and short answers are scored by the learner against the rubric; the system caps nothing but records hints, notes, reference use and timer use as declared. Mock results from yourself are capped at 80 by the existing evidence rule.
- **Seed problems link to LeetCode** by slug (no statements are stored); four are premium-only; a few difficulties changed on the platform over time and should be double-checked when you meet them.
- Interview rounds for "Python/backend", "concept" and "practical engineering" are rehearsed inside the existing DSA, CS and project rounds (no new round types, D-085).
- Browser sessions are one-user; there is no authentication by design (D-019).
- The seed YAML (~2 MB) now takes ~0.4 s to parse with libyaml (3.3 s without); the app loads the catalog from MySQL, not from YAML.

## G. Remaining genuine content-depth work

Bigger libraries are useful, not required: more SQL exercises (5 today), more guided problems per pattern (42 guided / 48 timed), more LLD cases (10), more behavioral questions per competency (30 total), and an independent technical review of the version-sensitive facts listed in the authors' reports. None of these blocks a skill from having a complete path.

## H. WHAT IS COMPLETE · PARTIALLY COMPLETE · CONTENT-DEPTH WORK · MUST NOT CHANGE

- **Complete:** the whole loop Learn → Practice → Evaluate → Evidence → Skill state → Gap → Revision → Mentor → Today → Mock → Readiness is wired end to end and verified in a real browser; no required skill has a dead end.
- **Partially complete:** learning-session steps for problems record attempts through the existing attempt form (one problem per step); the mentor does not yet choose between *Learn / Practice / Review / Test / Timed / Mock / Project / Behavioral* as separate decisions: it keeps choosing the stage, and the session turns that stage into the right kind of work (D-085).
- **Content-depth work:** §G.
- **Must not change without a new decision:** the evidence ladder and outcome points, gap/readiness/revision formulas, ruleset `v1`, the canonical skill graph and stable ids, the append-only observation rule, the rule that learning content only produces existing observations (LEARNING_ENGINE §1), the `seed-v1`/`seed-v2` locks.

## I. Operations

| Need | Command |
|---|---|
| Start | `make dev` (stack on `http://127.0.0.1:5173`, API `127.0.0.1:8000`; applies migrations and loads the catalog) |
| Checks | `make check` (Docker wrapper: `./scripts/make-in-docker.sh check`) |
| Backup / verify | `make backup` then `make backup-verify` (also nightly by the backup sidecar) |
| Reset preparation data (destructive, backs up first) | `make dev-reset CONFIRM=RESET-PREP-DATA` |
| Validate / load content | `make seed-validate`, `make seed`; while authoring: `python -m app.cli.catalog validate --draft --only learning/<file>.yaml` |

**Daily workflow:** open Today → follow the first mission: *Start the session* (or "Do it my way" for the timer-and-log flow) → finish each step honestly (closed-book checks, hints and reference only when needed) → read "what changed" → Revise when due. **Weekly:** Progress and the weekly review; log a mock when the Mocks page recommends one (Rehearse a round gives the prompts); check Roadmap for plan changes. Open Settings → Developer → Content coverage only when authoring content.

---

# Part III — Product/UX correction: personalised learning starts once enough is measured (D-086)

Date: 2026-10-06 · ruleset `v1` (unchanged) · catalog `seed-v2` (unchanged) · schema head `0012_learning` (**no migration**).

## Problem (from the real UI)

Calibration 6/12, 118/123 skills measured, Today says "We have enough evidence to build your initial roadmap", and the user can open the roadmap, yet Today shows only "Today's diagnostic work". "Where is my today learning?"

## Root cause (inspected before changing)

| Question | Answer |
|---|---|
| What switched Today to personalised mode? | Frontend: `calibrating = plan.calibration.active && baseline.phase !== 'COMPLETE'`. `calibration.active` is the planner's `calibration_mode` = battery incomplete **or** < 60% assessed. So Today stayed calibration-only until **12/12**. |
| What is "enough evidence"? | `calibration_phase() == ENOUGH_MEASURED`: battery open and assessed required skills ≥ `CALIBRATION_MIN_ASSESSED_PCT` (60). It only drove the UI hint and roadmap availability (D-080). |
| How did the mentor choose the day's work? | `generate_daily_plan`: while the battery was open it built **only** revision and baseline candidates; the gap engine's output was never turned into a mission. |
| How is a learning session created? | `POST /learning/sessions {skill, stage, plan_item_id}` (`learning_service`); `plan.learning` previews the session for a pending GAP/DIAGNOSTIC/REVISION/MAINTENANCE/FOLLOW_UP item (D-085). |
| How does Today get its mission? | `GET /today` (frozen daily plan) → `plan.items` + `plan.learning`. |
| How are plan items closed? | The session's completion records its observation with `plan_item_id`; the existing observation path marks the item DONE (audited). |

## Change (smallest possible; no second recommendation engine)

- `CalibrationStatus` gains `enough_measured` and the derived `hybrid` (enough measured **and** battery open). No constant changed.
- `generate_daily_plan`: on a hybrid day it additionally builds the **existing** `_gap_candidates`, admits at most one GAP mission and packs it first (learning > revisions > remaining battery). Below the threshold: unchanged. Battery complete: unchanged.
- `r_calibration` ("No new material until the baseline is complete") is silent on a hybrid day.
- Frontend: new `LearningMission` card; `TodayView` hybrid layout (learning → calibration → other work); `CalibrationCta` ENOUGH_MEASURED copy now says the assessments "don't block today's learning". Plans stay frozen: a plan made earlier in the day without a mission offers **Add today's learning** (existing `POST /plan/today/regenerate`, keeps DONE work); if the planner dropped the mission only for lack of time today it says the mission starts tomorrow.
- Docs: D-086, MENTOR_ENGINE §3, GLOSSARY, UI_SPEC §3.

## Today, before and after

| State | Before | After |
|---|---|---|
| < 60% measured | calibration only | **unchanged** |
| ≥ 60% measured, battery open (6/12, 118/123) | calibration only: "Today's diagnostic work" | **Today's learning** card first (focus, why, estimated time, session steps, *Start today's learning*), then the calibration card/progress/remaining calibration ("These assessments will continue to sharpen your roadmap, but they don't block today's learning"), then other work (revisions) |
| 12/12 | personalised mentor | **unchanged** |

## Verification

Test counts and results are in the table below (all actually run).

| Check | Result |
|---|---|
| Backend: ruff, ruff format, mypy (150 files, strict domain) | clean |
| Backend: pytest (full, own DB) | **533 passed** (523 before; +8 `tests/api/test_hybrid_today_api.py`, +2 unit: `hybrid` in `test_calibration_phase.py`, hybrid message in `test_calibration_message.py`) |
| Frontend: vue-tsc, eslint (0 warnings) | clean |
| Frontend: vitest | **189 passed** (23 files; +9 in `tests/today.spec.ts`: hybrid layout and order, Start opens the session for the plan item, Continue calibration/roadmap links, frozen-plan "Add today's learning", "starts tomorrow", no-content fallback, below-threshold calibration-only, complete = normal Today, a11y hooks) |
| Golden scenarios | unchanged and passing (no scenario number moved; no ruleset constant changed) |
| Migration | none needed; `alembic upgrade head` on an empty scratch DB ran to `0012_learning` |
| Backend behaviour proven | below threshold → battery only and `CALIBRATION` message; enough + open battery → exactly one GAP first, battery after, no `CALIBRATION` message, learning preview present; same inputs → same plan and `input_hash`; re-plan keeps DONE work and never duplicates a candidate key; a pre-threshold frozen plan stays frozen until re-planned; starting the session links `plan_item_id` and creates/removes no plan item; battery item still completes and counts; complete battery keeps the personalised plan |
| Browser (real Chrome 154, throwaway DB `mm_scratch`, real backend + Vite, onboarding done, sweep → `ENOUGH_MEASURED`) | Today shows the learning card first, calibration second; **Start today's learning** opened `/learn/session/1` (linked to plan item 1); *Continue calibration* → `/calibrate?start=1`; screenshots at 1440 and 390 px |
| Overflow | `scrollWidth == clientWidth` at 360 px on Today and on the session page |
| Accessibility (axe-core, WCAG 2 A/AA + best practice) | **0 violations** at 1440 px (38 rules passed) and 360 px (40 passed) on the hybrid Today |
| Real database (the user's app on :8000) | read-only checks only: `/baseline` = `ENOUGH_MEASURED`, 6/12, 118/123, 255 min left; the real Today now renders the hybrid layout. Row counts before/after identical (evidence 407, assessments 373, attempts 2, plans 2, plan items 6 (5 DONE), learning sessions 2, revision items 12). **Nothing was reset, deleted or rewritten.** |

**Known limitations**

- The daily plan stays frozen (by design). Today's existing plan on the user's database was made before this change, so it has no learning mission; it shows **Add today's learning**. On that day 70 of 90 minutes are already done and a 20-minute revision is pending, so a re-plan will not fit a mission; the mission arrives with tomorrow's plan. (I did not press re-plan on the real database.)
- On a hybrid day exactly one learning mission is planned; if the library has no session for that skill/stage, the ordinary mission card (timer-and-log flow) is shown instead of the learning card.
- The "learning path" shows the real session steps (lesson, concept check, practice…) from the mission library, not a fixed five-step list; the number of steps depends on the content that exists for that skill/stage.

**Next logical task:** none required for this correction; optionally tick the matching line in `IMPLEMENTATION_PLAN.md` if the owner tracks UX corrections there.
