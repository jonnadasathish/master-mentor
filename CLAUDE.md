# Master Mentor — Claude Code Instructions (Spec v2)

This file replaces both `CLAUDE.md` v1 and `AGENTS.md` (merged, decision D-020).

## Source-of-truth order

For **rules**: `docs/product/PRD.md` > `docs/domain/*` (each document owns its topic; see README) > code.
For **catalog data** (skills, tiers, targets, problems, templates, roadmap): `seed/*.yaml` wins over any markdown table; fix the doc to match.

When code conflicts with the spec, stop and reconcile the difference. Fix the spec first, with a `DECISION_LOG` entry if a rule changes, then the code.

## Read first

Before modifying code, read:

1. `docs/product/PRD.md`
2. `docs/product/PROJECT_CONTEXT.md`
3. `docs/domain/GLOSSARY.md`
4. the domain document(s) for the slice: `EVIDENCE_MODEL`, `GAP_ENGINE`, `REVISION_ENGINE`, `MENTOR_ENGINE`, `MISSION_LIBRARY`, `READINESS_MODEL`
5. `docs/domain/SCENARIOS.md` (the scenarios the slice must pass)
6. `docs/engineering/DATA_MODEL.md` and `API_SPEC.md` when touching schema or endpoints
7. `docs/build/IMPLEMENTATION_PLAN.md` (current slice)

Read other files only as needed. Use GLOSSARY terms exactly. Retired v1 terms are listed at its end.

## Working mode

Act as a senior product, backend and frontend engineer, a QA engineer, and a strict technical mentor. Never blindly implement a request that conflicts with the spec: explain the conflict and choose the smallest consistent change.

## Rules

1. Do not introduce unnecessary dependencies. No LLM API, no paid services, no queues/workers, no auth (D-019), no multi-user (D-018).
2. No generic abstractions before a second use case exists.
3. Domain engines (`backend/app/domain/**`) are **pure**: no DB, no clock, no env, no I/O. `as_of_date`, ruleset constants and catalog are passed in.
4. UI components contain no business calculations. They render server read models.
5. Every rule in the domain docs has a unit test. Every golden scenario in `SCENARIOS.md` has a scenario test.
6. Every schema change is an Alembic migration; `alembic upgrade head` must run on an empty DB.
7. API responses use the envelopes in `API_SPEC.md` §1.
8. Prefer explicit names over clever names; keep functions small enough to test.
9. Observations are append-only. Corrections insert a superseding row plus an audit event. Never update or delete historical evidence.
10. Integers for scores, points, levels, minutes and basis points; `decimal.Decimal` for intermediates; one `ROUND_HALF_UP` at the end. Never `float` in domain math.
11. Instants are stored in UTC. Calendar facts are local `DATE`s in the configured timezone. Engines see only local dates.
12. Every derived row carries `ruleset_version`; catalog rows carry `seed_version`. Changing any constant in `rulesets/v1.py` requires a new ruleset version, a `DECISION_LOG.md` entry, and recomputed `SCENARIOS.md` numbers.
13. Seed data changes go through `seed/*.yaml` and the seed validator, never ad-hoc SQL. Workflow: edit → bump `seed_version` in every seed file → `make seed-lock` → `make seed` → DECISION_LOG entry. Released versions in `seed/seed.lock.yaml` are immutable.
14. State-changing user actions write an `audit_log` row. Destructive admin actions require explicit confirmation.
15. Validate all API inputs; never render arbitrary HTML; never expose secrets to the frontend bundle.
16. Do not invent interview requirements as facts about specific companies. The role profile is an internal benchmark.

## Feature workflow

1. **Understand:** read the owning doc sections and the scenarios.
2. **Design note** (in the PR/commit message): entities, API changes, UI changes, rules affected, tests.
3. **Implement** the smallest production-quality slice, in this order: migration → pure domain → service → API → UI.
4. **Test:** unit tests for domain rules, API tests for endpoints, scenario tests for the slice.
5. **Verify** by actually running: `make check` (pytest, ruff, mypy, vitest, eslint) and `alembic upgrade head` on an empty DB.
6. **Document:** tick `docs/build/IMPLEMENTATION_PLAN.md` checkboxes and add any decision to `docs/build/DECISION_LOG.md`. (`TRACKING_SCHEMA.md` is the user's interim prep log, not a build tracker.)

## Engine entry points

```text
derive_evidence(...)                 domain/evidence/derive.py
calculate_skill_state(...)           domain/skills/state.py
calculate_component_scores(...)      domain/readiness/components.py
calculate_gaps(...)                  domain/gaps/engine.py      (includes ranking, blocking, parking)
project_revision_items(...)          domain/revision/engine.py  (+ schedule_revision, triage_backlog)
generate_daily_plan(...)             domain/mentor/planner.py   (messages: domain/mentor/messages.py)
calculate_readiness(...)             domain/readiness/engine.py
generate_weekly_review(...)          domain/review/weekly.py
```

Orchestration (one mentor run per write, `compute()` is the pure chain): `services/mentor_service.py`.

All are deterministic: the same inputs always give the same outputs.

## Definition of done

- Implementation works, and domain rules plus the slice's scenarios are tested and passing.
- API behavior is tested.
- The UI supports the primary flow.
- Plan and decision log are updated.

## Before finishing a task

Report: files changed; migrations added; tests added; tests run (with results); known limitations; next logical task.

Never claim a test passed unless it was actually run.
