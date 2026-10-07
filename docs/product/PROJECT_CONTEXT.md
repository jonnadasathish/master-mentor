# Master Mentor — Project Context (Spec v2)

## Owner context

- Personal, single-user project.
- Goal: maximum readiness for top product-company SWE interviews, at the `backend_fullstack_sde2` benchmark.
- Background: practical PHP, JavaScript, Vue, SQL and FastAPI. Wants to strengthen Python, DSA, CS, LLD, system design and interview execution.
- Time: **10 h/week of preparation** and **10 h/week of building** the app. They are separate budgets.
- The app is a tool for the preparation, not the deliverable. **Risk:** building can become a substitute for preparing. Mitigations:
  - preparation starts on day 1, logged in [`TRACKING_SCHEMA.md`](../build/TRACKING_SCHEMA.md) until the capture slice ships;
  - real logging is possible from Slice 3 (activity capture); backup arrives first thing in Slice 4.
- Preparation content (skills, profile, templates, roadmap) lives in `seed/*.yaml` and stays usable if the UI changes.

## Product philosophy

Master Mentor acts like a strict mentor:
- measure before teaching;
- find the weakness that matters most and explain why;
- prescribe the smallest high-impact practice at the right stage;
- record what happened as evidence;
- reschedule revision;
- escalate or de-escalate based on evidence only;
- say "not ready" until gates prove otherwise;
- teach what it prescribes: every skill has a learning path (lesson → check → practice → timed → recall), and completing it is evidence like any other practice (MASTER_SPEC_V3, LEARNING_ENGINE.md).

The promise is evidence-based readiness for strong product-company interviews, never a guaranteed interview, offer or salary.

## Architecture

A modular monolith:

```text
Vue 3 (capture + display only, no business calculations)
   ↓ JSON
FastAPI routers (validation only)
   ↓
Application services (load → call pure engines → persist mentor run)
   ↓
Pure domain engines (no I/O, as_of_date and ruleset injected)
   evidence → skill_state → components → revision projection → gaps → (triage, plan run only) → readiness → mentor
   ↓
Repositories (SQLAlchemy 2) → MySQL 8
```

Docker Compose (`docker-compose.yml`) runs `mysql`, `backend`, `frontend` and the `backup` sidecar. There are no queues, workers, event buses, caches or cloud services. A full recomputation (133 skills, a few thousand evidence rows) runs synchronously after each write.

Backend domains (packages under `backend/app/domain/`): `catalog`, `evidence`, `skills`, `gaps`, `revision`, `mentor`, `readiness`, `review`, and `learning` (content validation, grading, completion → observation mapping, sessions, practice resolution, coverage; it produces existing observations and owns no scoring rule).

## Determinism

The same:
- observations and recorded decisions (plans, revision item actions),
- `as_of_date`,
- active goal,
- `ruleset_version` and `seed_version`

produce identical:
- evidence, skill states, component scores, gaps and ranks,
- revision schedule,
- readiness state and blockers,
- daily plan (when generated) and mentor message.

Domain code never reads the clock, environment or database.

## Source of truth

| Kind | Examples | Rule |
|---|---|---|
| Authoritative (append-only) | observations, revision item actions, goal versions | never updated in place; corrections supersede; goal changes insert a new version |
| Content (editable, audited) | stories, projects, assessment prompts | edits audited; not evidence by themselves |
| Decisions (frozen) | daily plans, plan items, weekly reviews | written once; changes are audited |
| Derived (rebuildable) | evidence, skill states, gaps, revision items, readiness snapshots | recomputed per mentor run; carry `ruleset_version` |
| Catalog | `seed/*.yaml` | versioned by `seed_version` |

## Development rules

- No AI/LLM API in the product. Claude Code is used only for development.
- Build in vertical slices ([`IMPLEMENTATION_PLAN.md`](../build/IMPLEMENTATION_PLAN.md)). Engines come before UI shells.
- No user auth in MVP. The app binds to `127.0.0.1` only (decision D-019).

## UX principle

Open the app and the first screen answers, in order:
1. Where am I? (readiness state + blockers)
2. What should I do today? (plan)
3. Why? (explanation + message)
4. What should I stop? (stop list)

"Am I improving?" is answered on the Progress page.
