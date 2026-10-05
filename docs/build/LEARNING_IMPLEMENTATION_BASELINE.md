# Learning Implementation Baseline (MASTER_SPEC_V3 Phase A)

Date: 2026-10-05. Written **before** any V3 behavior change, from the repository and the running stack (not from the spec's own description of the state).

## 1. Verified starting point

| Check | Result |
|---|---|
| Backup + restore verification of the real preparation DB | `make backup` + `make backup-verify` → `RESTORE VERIFIED: mastermentor-20261005T110258Z.sql.gz` (39 tables, row counts and checksums equal) |
| Last full `make check` (after D-082) | exit 0 — backend 478 passed, frontend 165 passed, ruff, mypy (137 files), vue-tsc, eslint clean |
| Alembic head | `0011_starting_profile` (11 migrations, `0001_baseline` … `0011_starting_profile`) |
| Seed | `seed-v1`, locked in `seed/seed.lock.yaml` (catalog `7546c05d…`) |
| Real DB content (read-only look) | 133 skills, 44 problems, 86 mission templates, 12 baseline items; user data: 1 starting profile, 4 goal versions, 123 assessments (the sweep), 2 attempts, 1 mock, 6 revision items, 1 daily plan |

D-078 (UI V2), D-079 (empty message clause), D-080 (starting profile + calibration), D-081 (Continue calibration) and D-082 (battery work closes its plan item) are all present in code, tests and `DECISION_LOG.md`; nothing to reconcile.

## 2. What exists (the intelligence layer)

Architecture: Vue 3 + Pinia → FastAPI routers (`app/api/v1`, 18 modules, ~80 endpoints) → services (`app/services`, 21) → pure domain (`app/domain`: activity, baseline, catalog, evidence, gaps, mentor, profile, readiness, review, revision, roadmap, rulesets, skills) → SQLAlchemy repositories → MySQL 8.4. Domain purity is enforced by an AST test.

| Area | State |
|---|---|
| Skill graph | 22 groups, 133 skills (dsa 44, cs 24, system_design 22, coding 14, behavioral 12, project 11, lld 6); tiers T1 35, T2 56, T3 32 (123 required), T4 10 |
| Evidence | L0–L7 ladder; problem attempts, 13 assessment kinds, mocks, revision reviews; `source_key` gives diversity |
| Gap / revision / mentor / readiness | deterministic engines with golden scenarios; mentor stages DIAGNOSE … SIMULATE, mission templates per component + stage; readiness gates per component (dsa, coding, cs, lld, system_design, behavioral, project) |
| Practice capture | problem attempts (44 seeded LeetCode problems + personal problems), assessment forms, mocks (round types DSA, CS, LLD, SYSTEM_DESIGN, BEHAVIORAL, PROJECT_DEEP_DIVE + final simulation), stories/projects/prompts (personal content) |
| Plan / Today | frozen daily plan, mission cards with "why", calibration-first Today, personal roadmap, current state |

## 3. Existing content coverage (the gap this spec addresses)

There is **no teaching content at all**. A mission says *what* to do ("CS: learn — 25 min study, one-page notes, 5-question quiz") but the app contains no lesson, no quiz question, no exercise text, no rubric checklist and no interview question. The user must bring the material.

Practice coverage by skill (seed-v1):

| Component | Skills | With ≥ 1 mapped problem | Practice the app can actually present |
|---|---:|---:|---|
| dsa | 44 | 38 | problems only (no lesson, no concept check); 6 skills have none: `dsa.complexity_analysis`, `graph.mst`, `dp.interval_state_machine`, `dp.tree`, `math.number_basics`, `dsa.pattern_recognition` (drill-only) |
| coding (Python + execution) | 14 | 1 | nothing concrete; the skill page's Start goes to the problem list filtered by the skill → **"No problems match."** |
| cs | 24 | 0 | a free-form "log an assessment" form |
| lld | 6 | 0 | free-form form |
| system_design | 22 | 0 | free-form form |
| behavioral | 12 | 0 | stories (personal) + free-form form |
| project | 11 | 0 | free-form form |

Dead ends confirmed in code: `SkillDetailView` sends every `dsa`/`coding` skill to `/prepare/dsa/problems?skill=…`; `ProblemsView` then shows only "No problems match." for the 19 coding/dsa skills without a mapped problem (e.g. Complexity analysis, every Python skill).

Problem metadata: id, platform key, title, difficulty, expected minutes, skill mapping. No pattern, hints, expected complexity, common mistakes, prerequisites or interview relevance. No per-problem progress state beyond the attempt list.

## 4. Learning-domain gap analysis

| Spec section | Exists | Missing |
|---|---|---|
| §6 content model (17 types, stable ids, skill mapping) | — | everything |
| §7 learning session | mission cards (one observation per mission) | multi-step session, resume, before/after |
| §8 dead-end rule | — | case A–D resolution, honest content-gap state |
| §9/§11 practice states | attempt rows | derived per-problem state (seen … interview-grade); problem guide metadata |
| §10–§19 curricula | skill graph + mission templates | lessons, checks, exercises, cases, projects, behavioral question bank |
| §20 mocks | mock capture + readiness rules | per-round prompt kits (questions, rubric, follow-ups) |
| §21 adaptive mentor | full deterministic mentor | attaching learning content to the missions it already chooses |
| §22 Today | mission cards | missions that open a concrete lesson / check / exercise session |
| §26 coverage audit | — | deterministic report + developer page |
| §27 seed authoring | YAML + validator + lock | `seed/learning/*` + validation |

## 5. Implementation map (decisions taken here, recorded as D-083)

Principle: the learning layer **produces existing observations**; it adds no evidence formula, no gap/readiness rule and no second skill system.

1. **Content catalog** — `seed/learning/curriculum.yaml` (tracks → topics → skills) and `seed/learning/<track>.yaml` (content items). Loaded by the existing validator/loader into new catalog tables (`learning_tracks`, `learning_topics`, `learning_topic_skills`, `learning_content`, `learning_content_skills`) under one new `seed_version` (`seed-v2`, locked). Content body is stored as validated JSON; keys are stable.
2. **Completion → evidence** (pure `domain/learning/evidence.py`): lesson / worked example / visual → `STUDY_SESSION` (L0, minutes); concept check / quiz / revision cards → `RECALL_QUIZ` graded on the **server** (L1 closed-book, L0 with notes); exercises, cases, interview and behavioral questions → their existing practice kinds (`CODE_EXERCISE`, `CONCEPT_EXPLAIN`, `LLD_DESIGN`, `MACHINE_CODING`, `SD_DESIGN`, `ESTIMATION_DRILL`, `STORY_REHEARSAL`, `PROJECT_WALKTHROUGH`, `APPLIED_TASK`) with `outcome_points` from a deterministic rubric score and `followup_points` from the follow-up rubric; guided/timed problems → ordinary problem attempts. `source_key = content:<key>`. Recorded through `AssessmentService` / `ActivityService` (same validation, audit and mentor run).
3. **Progress** — derived from the user's observations by `source_key` (no progress table).
4. **Learning sessions** — new user tables `learning_sessions` + `learning_session_steps` (state machine, audited); steps composed by a pure function from (skill, mentor stage, minutes, catalog, what is already done). A session started from a plan item closes it through the existing plan completion step (D-082 path).
5. **Skill learning read model** — `GET /skills/{key}/learning`: why it matters, Learn / Practice / Test / Revision tabs, practice resolution case A–D, related skills, next action.
6. **Problem bank** — curated additions with stable new ids; `problems.guide_json` (pattern, complexity, hints, mistakes, prerequisites, relevance); derived practice state per problem.
7. **Mentor / Today** — the planner is unchanged; plan items gain a read-only `learning` preview (the steps a session would contain) and Start opens the session.
8. **Coverage report** — pure function + `GET /learning/coverage` + Developer page; a test fails if any required skill is `CONTENT_GAP`.
9. **Mocks** — round kits as content (`interview_question` sets per existing round type); no new round types, no readiness change.

Order: B foundation (schema, seed, validator, loader, evidence mapping, sessions) → C skill page + dead-end fix → D DSA → E Python + CS → F LLD + SD → G engineering, projects, behavioral → H mock kits → I/J mentor + Today integration → K coverage → L UX hardening → M audit.
