# Master Mentor — Progress

Status as of 2026-10-06. Source of truth: `docs/build/IMPLEMENTATION_PLAN.md`, `DECISION_LOG.md`.

## 1. Goal
- Private, single-user interview-prep system for FAANG-style SWE loops (PRD §1).
- Measures demonstrated skill, ranks gaps, plans today's work, enforces revision, gates "ready".
- Deterministic pure domain engines; no LLM, no auth, no multi-user.

## 2. Done (committed)
- Slices 0–2 spec, foundation, catalog: `docker-compose.yml`, `backend/app/domain/rulesets/v1.py`, `app/domain/catalog/`, `seed/*.yaml`, `seed/seed.lock.yaml`.
- Slice 3 activity capture: migration `0003`, `/problems`, `/problem-attempts`.
- Slice 4 evidence + skill state: `domain/evidence/derive.py`, `domain/skills/state.py`, backup/export/reset.
- Slice 5 gaps: `domain/gaps/`, `domain/readiness/components.py`, goals/settings.
- Slice 6 revision: `domain/revision/`, `/revisions`.
- Slice 7 mentor/plan: `domain/mentor/`, `/today`, plan actions.
- Slice 8 readiness: `domain/readiness/engine.py`, `/readiness`.
- Slices 9–12 dashboard, mocks, weekly review, hardening: `domain/review/weekly.py`, export/import, replay audit; `docs/build/FINAL_AUDIT.md`.
- UI/UX V2 + starting profile (migration `0011`): last recorded 474 backend / 157 frontend tests.

## 3. In progress (uncommitted, 52 changed entries)
- MASTER_SPEC_V3 learning layer: plan ticks Phases A–M, but no test counts recorded.
- Backend: migration `0012_learning.py` (modified, not new), `services/learning_service.py`, `api/v1/learning.py`, `schemas/learning.py`, `infrastructure/seed_files.py`.
- Content: 17 new files in `seed/learning/` (58 total); `seed.lock.yaml` has new `learning:*` fingerprints.
- Frontend: `components/learning/MockKits.vue`, `views/settings/CoverageView.vue`, router, `ProblemDetailView.vue`.
- Docs: new `docs/domain/LEARNING_ENGINE.md`; D-083 to D-085 added.
- Stopped at: nothing verified after the latest edits. `make check` and an empty-DB `alembic upgrade head` are not confirmed.

## 4. Remaining (one session each)
1. Verify V3: `make check`, empty-DB migration, fix failures.
2. Reconcile the seed lock: `seed-validate`, `seed-lock`, `seed`, `seed-status`.
3. Decide whether `0012` is amended or split into `0013` (was it applied anywhere?).
4. Commit V3 in logical commits (migration+backend, seed, frontend, docs).
5. Record real test counts and update `IMPLEMENTATION_PLAN.md`, `FINAL_AUDIT.md`.
6. Browser validation of learning flows at 1440 and 390 px.
7. Content review: coverage report shows no required skill is CONTENT_GAP/UNMEASURED.

## 5. Decisions to keep
- Rules: PRD > domain docs > code. Seed YAML wins over markdown tables.
- Domain is pure (AST-enforced, D-041/D-076). Only `SystemClock` reads the wall clock.
- Observations are append-only; corrections supersede + audit.
- One `seed_version` (D-044). Fingerprints are frozen per version in `seed.lock.yaml`.
- Released versions are immutable; `seed-v1` frozen, `seed-v2` locked once at end of V3 (D-084). Test mutations use `seed-v3`.
- Seed workflow: edit, bump version in every file, `make seed-lock`, `make seed`, log decision.
- Personal problems use `seed_version='user'`, ids ≥ 1,000,000 (D-050).
- Export v2 with `id_maps`; import only into an empty DB, preview then commit (D-075).
- Learning completion records existing observations (`source_key=content:<key>`); no engine rule changed (D-083).
- Integers and ROUND_HALF_UP only; no floats in domain math.

## 6. How to run
- Quality gate: `make check` (lint, typecheck, tests). Pieces: `make lint`, `make typecheck`, `make test`.
- Start stack: `make dev`; stop: `make down`; logs: `make logs`.
- DB only: `make db-up`, `make db-migrate`.
- Seed: `make seed-validate`, `make seed`, `make seed-lock`, `make seed-status`.
- Safety: `make backup`, `make backup-verify`, `make export`.
- Destructive (needs CONFIRM): `make dev-reset`, `make restore-live`.

## 7. Next step
- Run `make check` and `alembic upgrade head` on an empty DB to see whether the V3 working tree is green. Fix before committing anything.
