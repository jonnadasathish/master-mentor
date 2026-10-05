# Master Mentor — Implementation Plan

## Phase 0 — Repository setup

- [ ] Initialize Vue 3/Vite
- [ ] Initialize FastAPI
- [ ] Create MySQL Docker service
- [ ] Configure environment variables
- [ ] Add Alembic
- [ ] Configure lint/test tooling
- [ ] Add `CLAUDE.md`, `AGENTS.md`

## Phase 1 — Auth and Goal

- [ ] User model
- [ ] password hashing
- [ ] session/cookie auth
- [ ] goal model
- [ ] goal UI
- [ ] migration tests

## Phase 2 — Skill Graph

- [ ] skill schema
- [ ] relationships
- [ ] role requirements
- [ ] seed canonical skill tree
- [ ] skill browser UI
- [ ] skill detail UI

## Phase 3 — DSA Tracking

- [ ] problem schema
- [ ] problem-pattern mapping
- [ ] attempt schema
- [ ] attempt API
- [ ] quick-log UI
- [ ] skill observation creation
- [ ] unit tests

## Phase 4 — Evidence + Skill Engine

- [ ] evidence schema
- [ ] scoring service
- [ ] confidence calculation
- [ ] ruleset versioning
- [ ] recalculation endpoint
- [ ] test fixtures

## Phase 5 — Gap Engine

- [ ] gap schema
- [ ] role target lookup
- [ ] raw gap calculation
- [ ] priority factors
- [ ] dependency handling
- [ ] reason codes
- [ ] ranked gap endpoint
- [ ] deterministic tests

## Phase 6 — Revision Engine

- [ ] revision schema
- [ ] interval logic
- [ ] completion endpoint
- [ ] due/overdue queries
- [ ] revision UI
- [ ] tests

## Phase 7 — Daily Mentor

- [ ] mission model
- [ ] plan model
- [ ] priority ranking
- [ ] time allocation
- [ ] reason explanations
- [ ] Today page
- [ ] complete/skip/defer

## Phase 8 — Dashboard + Weekly Review

- [ ] readiness service
- [ ] gates
- [ ] dashboard
- [ ] weekly aggregation
- [ ] review UI
- [ ] next-week focus

## Phase 9 — System Design / CS / Practical / Behavioral

Implement each as the same abstraction:

`Skill → Practice → Evidence → Revision → Gap`

## Phase 10 — Mock Interviews

- [ ] mock entity
- [ ] dimension scoring
- [ ] trend
- [ ] gap integration
- [ ] mock UI

## Phase 11 — Backup/export

- [ ] JSON export
- [ ] CSV export
- [ ] import preview
- [ ] import commit
- [ ] nightly backup
- [ ] backup status UI

## Phase 12 — Hardening

- [ ] security review
- [ ] API validation
- [ ] database indexes
- [ ] backup restore test
- [ ] deterministic replay test
- [ ] browser testing
- [ ] accessibility pass
- [ ] performance baseline

## Execution rule

Never implement more than one major vertical slice at once.

For each slice:
1. schema
2. service
3. API
4. tests
5. UI
6. integration test
7. documentation update
