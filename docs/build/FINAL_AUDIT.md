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
