# Master Mentor — Product Requirements Document (Spec v2)

## 1. Product

**Name:** Master Mentor

**Positioning:** A private, single-user interview-preparation system. It continuously measures what you can *demonstrate*, finds the weaknesses that matter most for the target loop, tells you the highest-value work for today and why, enforces revision, and refuses to call you ready until gates are met.

**Primary goal:** Maximum readiness for top product-company / FAANG-style Software Engineer interviews.

**User:** one person, the owner. There is no multi-user support.

**Target profile (locked default):** `backend_fullstack_sde2` (see [`ROLE_PROFILE.md`](../domain/ROLE_PROFILE.md)):
- Software Engineer, Backend/Full-Stack, at a mid-level / SDE-2 benchmark.
- Declared loop: DSA ×2, CS fundamentals, LLD/machine coding, system design, behavioral, project deep dive, final mixed simulation.
- This is an internal benchmark, not a claim about any company.

**Time:** 10 h/week of preparation (default Mon–Fri 90 min, Sat–Sun 75 min) and, separately, 10 h/week of building this application.

## 2. Product principles

1. Practice over passive consumption. Study time is recorded but never counts as evidence.
2. Evidence over self-report. Self-rating never raises a score.
3. One clear next action, with its reason.
4. Revision starts on day 1 and is a closed-book test, not a reminder.
5. Deterministic: the same state + date + ruleset + seed gives the same output.
6. Every recommendation is explainable from stored numbers.
7. The system must be able to say "not ready". The readiness state comes from gates, never from an average.
8. Optimize for interview readiness, never for feature count.

## 3. Questions the product must answer

| # | Question | Answered by |
|---|---|---|
| 1 | Where am I now? | Readiness state + component scores + skill matrix (`READINESS_MODEL`, `EVIDENCE_MODEL`) |
| 2 | What are my biggest weaknesses? | Ranked gaps (`GAP_ENGINE` §10) |
| 3 | Why are they weaknesses? | Gap type + reason codes + metrics (`GAP_ENGINE` §6, §9, §11) |
| 4 | What should I do today? | Daily plan (`MENTOR_ENGINE`) |
| 5 | Why today? | Plan item explanation + mentor message (`MENTOR_ENGINE` §9) |
| 6 | What evidence proves improvement? | Evidence ladder L0–L7 + before/after deltas on completion |
| 7 | What should I revise? | Revision queue (`REVISION_ENGINE`) |
| 8 | What should I stop studying? | Stop list: PARKED, OVER_TARGET, STUDIED_NOT_TESTED (`MENTOR_ENGINE` §8) |
| 9 | What prevents interview readiness? | Blockers (`READINESS_MODEL` §8) |
| 10 | Am I actually ready? | Readiness state; INTERVIEW_READY requires G0–G9 |

## 4. Non-goals

- Multi-user SaaS, social features, job-application tracking, resume builder, native mobile app.
- LLM chat or any LLM API in the product.
- Company scraping; automatic LeetCode import in MVP.
- Hiring or outcome guarantees.
- Paid external services.

## 5. Functional requirements

### Calibration and goal

| ID | Requirement | Priority |
|---|---|---|
| FR-1 | Create a goal: role profile, target date (optional), per-weekday budget. | Must |
| FR-2 | Run the baseline battery (M0) with a familiarity sweep; declared unknowns are recorded. | Must |
| FR-20 | First-run **Starting Profile** (experience, stack, target, time, optional self-reported strengths/weaknesses/never-studied/recently-studied topics). Self-reported context is stored apart from evidence and never enters an engine (D-080). | Must |
| FR-21 | A **calibration** entry point and status (not started / in progress / enough measured / complete) with progress, minutes and an estimate; the baseline is spread across the normal daily budget, never demanded at once. | Must |
| FR-22 | A **personal roadmap** (build / consolidate / sharpen / maintain / parked, plus not-yet-measured) and a **current state** that shows self-reported context beside measured values, both derived from the engines' output. | Must |

### Capture (observations)

| ID | Requirement | Priority |
|---|---|---|
| FR-3 | Log problem attempts with outcome, timer, hints, solution viewed, pattern identified, mistakes, explanation, complexity, follow-up, execution rubric, self-ratings, backdated date. | Must |
| FR-4 | Log assessments of every kind in `EVIDENCE_MODEL` §5.4, with per-skill outcome points from rubric cards. | Must |
| FR-5 | Log mocks with rounds, per-skill outcomes, weaknesses, and source (SELF/PEER/PLATFORM); flag final simulations. | Must |
| FR-6 | Manage behavioral stories (many competencies) and projects for deep dive. | Must |
| FR-7 | Correct any observation by superseding it (append-only + audit). | Must |

### Engines

| ID | Requirement | Priority |
|---|---|---|
| FR-8 | Derive evidence and skill state (level, score, confidence, effective score) after every write. | Must |
| FR-9 | Compute ranked gaps with type, reasons, blockers, parking, recommended focus. | Must |
| FR-10 | Create and schedule revision items automatically. PASS/PARTIAL/FAIL rescheduling, leech handling, backlog triage. | Must |
| FR-11 | Generate one frozen daily plan within budget, with stop list and one mentor message. | Must |
| FR-12 | Complete / skip (with reason) / defer plan items; completion records evidence and returns before/after deltas. | Must |
| FR-13 | Compute readiness state, gates, blockers, and daily snapshots. | Must |
| FR-14 | Auto-generate the weekly review; accept a reflection. | Must |

### State and safety

| ID | Requirement | Priority |
|---|---|---|
| FR-15 | Rebuild all derived state from observations and recorded decisions (`POST /admin/rebuild`). | Must |
| FR-16 | Version formulas (`ruleset_version`) and catalog (`seed_version`) on every derived row. | Must |
| FR-17 | JSON export of all data. | Must |
| FR-18 | Nightly MySQL dump with 14-day retention and a tested restore. | Must |
| FR-19 | CSV export and import API (preview/validate/commit into an empty database) — moved into scope by D-057/D-075; backup-age warning (D-075). Authentication stays out of scope. | Should (done) / Won't (auth) |

A plan never exceeds its budget. A revision backlog that exceeds the budget is handled by triage, not by overfilling (this replaces v1 FR-24).

## 6. Readiness

Readiness is owned entirely by [`READINESS_MODEL.md`](../domain/READINESS_MODEL.md):
- seven components with weights;
- gates G0–G9;
- states NOT_MEASURED / FOUNDATION / DEVELOPING / INTERVIEW_READY / STRONG.

The thresholds are internal benchmark values, not a claim about any company's hiring bar.

## 7. Acceptance (MVP complete)

The user can:

1. Create a goal and complete the baseline battery.
2. Log attempts, assessments and mocks in ≤ 30 seconds for the common case.
3. See skill states and ranked gaps with reasons.
4. Receive a frozen, explainable daily plan with a stop list and message.
5. Complete missions and see before/after deltas.
6. Have revisions created, scheduled, triaged and reviewed automatically.
7. See the readiness state with blockers, honestly NOT_MEASURED/FOUNDATION when appropriate.
8. Complete weekly reviews.
9. Export JSON, and restore from a nightly dump.
10. Rebuild all derived state and get identical outputs. All 20 golden scenarios (`SCENARIOS.md`) pass.

## 8. Success criteria (for the preparation, measured by the app)

- Readiness reaches INTERVIEW_READY with all gates passing, sustained ≥ 14 days.
- ≥ 80% plan completion and ≥ 70% revision pass rate over the final 8 weeks.
- No T1 skill below floor during the final 4 weeks.
