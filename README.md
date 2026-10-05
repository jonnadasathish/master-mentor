# Master Mentor

A private, single-user web app for preparing for top product-company Software Engineer interviews. It measures what you can demonstrate (evidence levels L0–L7), finds the weaknesses that matter most for the declared interview loop, plans each day, enforces revision, and refuses to report "interview-ready" until every gate passes.

**Status:** Specification v2 is frozen. Slices 1 (Foundation), 2 (Catalog) and 3 (Activity Capture) are done; see ([`docs/build/IMPLEMENTATION_PLAN.md`](docs/build/IMPLEMENTATION_PLAN.md)).

## Stack

- Vue 3 + Vite (capture and display only)
- FastAPI + Python, pure domain engines
- MySQL 8 + Alembic
- Docker Compose, bound to 127.0.0.1
- No LLM API, no paid services, no auth in MVP

## Getting started

Requirements: Docker with Compose v2. Make is optional: without it, use `./scripts/make-in-docker.sh <target>`.

```sh
cp .env.example .env        # then replace every CHANGE_ME value
make dev                    # build, start mysql + backend + frontend, wait for healthy, run migrations
```

- App: http://127.0.0.1:5173 opens **Today** (what to do today, why, how long, and how you are doing)
- First run: `/onboarding` (starting profile) → `/calibrate` (calibration hub) → `/roadmap` (your personal roadmap)
- Prepare (DSA, CS, System Design, LLD, Behavioral): `/prepare` · Revise: `/revise` · Mocks: `/mocks` · Progress: `/progress` · Roadmap: `/roadmap`
- Log practice: `/log` · baseline assessments: `/baseline` · weekly review: `/review`
- Developer / System tools (health, versions, catalog check, reset procedure) live under Settings → Developer: `/settings/developer`
- API health: http://127.0.0.1:8000/api/v1/health
- MySQL: 127.0.0.1:3307 (`MYSQL_HOST_PORT`)

Everything binds to 127.0.0.1 only. There is no authentication; do not expose these ports.

**Data safety.** Raw observations are append-only (corrections are new rows). Derived tables can be rebuilt any time with `POST /api/v1/admin/rebuild`. Backups land in `./backups` (git-ignored); restore with `make restore-live`. Developer reset procedure (never automatic): `make dev-reset CONFIRM=RESET-PREP-DATA` → backup → delete preparation data → the next page load recalculates from the kept catalog.

| Command | What it does |
|---|---|
| `make dev` | start the stack and apply migrations |
| `make db-up` / `make db-migrate` | start MySQL / `alembic upgrade head` |
| `make seed-validate` | validate `seed/*.yaml` (no writes; non-zero exit on errors) |
| `make seed` / `make seed-status` | load the catalog idempotently / show the loaded version |
| `make seed-lock` | freeze fingerprints of a new `seed_version` |
| `make lint` | ruff + ruff format check + eslint (zero warnings) |
| `make typecheck` | mypy (strict on `app.domain`) + vue-tsc |
| `make test` | pytest (unit, API, migrations on the `_test` DB) + vitest |
| `make check` | lint + typecheck + test: required before a slice is done |
| `make format` | auto-format backend and frontend |
| `make backup` | dump the DB now into `./backups` (the `backup` service also does this nightly at `BACKUP_HOUR_UTC`, keeping 14 days) |
| `make backup-status-check` | check that the running backup and backend containers share `./backups` and the backup-status endpoint reports the latest file (after changing `docker-compose.yml`, recreate containers with `make dev`) |
| `make backup-verify` | back up, restore into a scratch DB and compare row counts + checksums of every table |
| `make restore-live FILE=backups/<f>.sql.gz CONFIRM=RESTORE-LIVE-DATABASE` | **destructive**: replace the live DB (takes a safety backup first) |
| `make export` | JSON export + CSV zip of all preparation data into `./exports` (also `GET /api/v1/export/json`, `/export/csv`) |
| `make dev-reset CONFIRM=RESET-PREP-DATA` | **development only**: back up, then delete all preparation data (attempts, assessments, personal problems, derived state); keeps the catalog and settings; audited |
| `make frontend-deps` | rebuild after `frontend/package.json` changes |
| `make down` | stop (the data volume is kept) |

## Layout

```text
backend/    FastAPI app: api/ (routes), services/, domain/ (pure: rulesets, clock, canonical hashing),
            repositories/, models/, schemas/, infrastructure/ (db, system clock), alembic/, tests/
frontend/   Vue 3 + Vite + TypeScript + Pinia: api client, stores, router (7 pages), error boundary, tests/
docker/     Dockerfiles and MySQL init script
seed/       catalog YAML (loaded from Slice 2)
docs/       specification
```

## Core loop

Calibrate → evidence → skill state → gaps → daily plan → practice → evidence → revision → mocks → readiness gates → repeat.

## Documents

| Area | File | Owns |
|---|---|---|
| Product | [`docs/product/PRD.md`](docs/product/PRD.md) | requirements, acceptance |
| | [`docs/product/PROJECT_CONTEXT.md`](docs/product/PROJECT_CONTEXT.md) | owner context, architecture, determinism, source of truth |
| | [`docs/product/ROADMAP.md`](docs/product/ROADMAP.md) | tracks, milestones, baseline battery, weekly allocation |
| Domain | [`docs/domain/GLOSSARY.md`](docs/domain/GLOSSARY.md) | one meaning per term |
| | [`docs/domain/ROLE_PROFILE.md`](docs/domain/ROLE_PROFILE.md) | benchmark parameters (weights, tiers, gate thresholds) |
| | [`docs/domain/SKILL_GRAPH.md`](docs/domain/SKILL_GRAPH.md) | 133 skills, prerequisites, tiers |
| | [`docs/domain/EVIDENCE_MODEL.md`](docs/domain/EVIDENCE_MODEL.md) | evidence ladder, scoring, confidence |
| | [`docs/domain/GAP_ENGINE.md`](docs/domain/GAP_ENGINE.md) | gaps, priority, types, blocking, parking |
| | [`docs/domain/REVISION_ENGINE.md`](docs/domain/REVISION_ENGINE.md) | revision items, intervals, leeches, capacity |
| | [`docs/domain/MENTOR_ENGINE.md`](docs/domain/MENTOR_ENGINE.md) | daily plan, stop list, messages, weekly review |
| | [`docs/domain/MISSION_LIBRARY.md`](docs/domain/MISSION_LIBRARY.md) | mission templates, rubric cards |
| | [`docs/domain/READINESS_MODEL.md`](docs/domain/READINESS_MODEL.md) | gates, states, blockers (sole owner) |
| | [`docs/domain/SCENARIOS.md`](docs/domain/SCENARIOS.md) | 20 golden acceptance scenarios |
| Engineering | [`docs/engineering/DATA_MODEL.md`](docs/engineering/DATA_MODEL.md) | tables, constraints, indexes, DB rules |
| | [`docs/engineering/API_SPEC.md`](docs/engineering/API_SPEC.md) | REST contract |
| | [`docs/engineering/UI_SPEC.md`](docs/engineering/UI_SPEC.md) | 7 pages |
| Build | [`docs/build/IMPLEMENTATION_PLAN.md`](docs/build/IMPLEMENTATION_PLAN.md) | slices and checkboxes |
| | [`docs/build/DECISION_LOG.md`](docs/build/DECISION_LOG.md) | every spec decision |
| | [`docs/build/TRACKING_SCHEMA.md`](docs/build/TRACKING_SCHEMA.md) | interim prep log until Slice 3 (DSA attempts); still used for non-DSA work until Slice 4 |
| Seed data | [`seed/`](seed/) | skills, role profile, problems, roadmap, mission templates (source of truth for data) |

`docs/_v1_archive/` holds the original v1 kit for reference only. It is not authoritative and may be deleted.

## Working with Claude Code

Read [`CLAUDE.md`](CLAUDE.md) first.
