# Master Mentor — Golden Scenarios (Spec v2, ruleset `v1`, `seed-v1`)

These 20 scenarios are the executable acceptance contract for the mentor engines. Each becomes a test in `backend/tests/scenarios/` with a fixture builder. A scenario test asserts every **Expected** line. Values not listed are not asserted.

All numbers were computed with the formulas in `EVIDENCE_MODEL`, `GAP_ENGINE`, `REVISION_ENGINE`, `MENTOR_ENGINE` and `READINESS_MODEL`. If a formula changes, these numbers must be recomputed in the same change, together with a ruleset version bump and a `DECISION_LOG` entry.

## 0. Shared fixtures

**F0 (date, profile):**
- `as_of_date = 2026-11-02` (Monday).
- Profile `backend_fullstack_sde2`, ruleset `v1`, `seed-v1`.
- Daily budget 90.
- `target_date = 2027-06-28` (34.0 weeks, **BUILD**) unless stated.
- Rows written `row(level, points, age_days, source)`, MEDIUM difficulty, primary mapping unless stated.

**BG (background "at target"):** every skill not overridden by the scenario is at its target with HIGH confidence:

| Tier | Level | Score = effective |
|---|---|---:|
| T1 | L5 | 80 |
| T2 | L5 | 75 |
| T3 | L4 | 65 |
| T4 | L3 | 50 |

- T1–T3 skills last practiced 3 days ago, with practice minutes evenly spread (so there is no OVER_TARGET stop entry). T4 skills last practiced 40 days ago, with no practice minutes in the last 14 days.
- No failures; no mock weakness flags.
- BG component scores: dsa **76**, coding **73**, cs **75**, lld **77**, system_design **76**, behavioral **75**, project **73**; weighted **75**. All G2 gates pass.

**M-OK (mocks):**
- 14 rounds in the last 60 days: DSA 4, every other type 2, ≥ 1 PEER round per type.
- Last 6 round scores (newest first): 78, 76, 75, 77, 74, 76 (mean 76). Latest per type ≥ 70.
- Latest round dates: DSA 10-28, CS 10-26, PROJECT_DEEP_DIVE 10-25, BEHAVIORAL 10-24, LLD 10-22, SYSTEM_DESIGN 10-20.
- No final simulations.

**R-OK (revision):** 20 reviews in the last 30 days, 17 PASS (85%). No ACTIVE item has `due_date ≤ as_of`.

**Tracks:** last-7-day minutes equal each track's weekly allocation (no TRACK_FLOOR).

**BG readiness:** G0–G8 pass, G9 fails → **DEVELOPING**, `simulation_eligible = true`, blockers `[G9: 0 of 3 final simulations]`.

**BG plan:** no candidates exist (no gaps, nothing due, last mock 5 days ago, budget < 160).

---

## S01 — Cold-start developer

- **Given:** F0. Goal created today. No observations. Calibration mode (battery incomplete).
- **State:** all 161 skills unassessed (`score = null`, confidence NONE).
- **Input evidence:** none.
- **Expected skill state:** all UNASSESSED. Assessed required = 0/123.
- **Expected gaps:**
  - 32 root skills have status UNASSESSED; the other 129 are BLOCKED by unassessed prerequisites. (D-087: seed-v3 added 28 optional T4 communication skills, one of them a root; the blocking logic is unchanged. Before seed-v3: 31 and 102 of 133.)
  - Assessment priorities: `dsa.complexity_analysis` 100 (5 downstream), `python.core_syntax` 100 (8), `db.sql_querying` 100 (3), `behavioral.ownership` 100 (0), `sd.capacity_estimation` 75 (0), `bit_manipulation.core` 20 (0).
  - Gap type UNASSESSED, focus DIAGNOSE.
- **Expected priority:** ranking is actionable UNASSESSED roots by priority desc, importance desc, key asc. The first is `behavioral.impact` (100, T1).
- **Expected revision state:** no items.
- **Expected daily plan** (calibration: battery in order, full budget):
  1. `M0-B01` familiarity sweep, 15 min.
  2. `M0-B02` DSA diagnostic A, 60 min. Greedy-cover picker → problems **#4 `3sum`**, then **#2 `group-anagrams`**.

  Total 75. `M0-B03` (30) and every later item don't fit. Unallocated 15.
- **Expected mentor message:** `CALIBRATION`: "Calibration: 0/123 required skills measured. Today's diagnostics: M0-B01, M0-B02. No new material until the baseline is complete."
- **Expected readiness:** **NOT_MEASURED**. Blockers: G0 for every component (assessed 0% < 70%), in order behavioral, coding, cs, dsa, lld, project, system_design. `weighted_score = 0`.

## S02 — Strong DSA, weak system design

- **Given:** F0 + BG. Override: all 22 `system_design` skills are at L3, score 50, MEDIUM, from untimed rows; ≤ 1 failure in the last 5; system_design track got 30 min in the last 7 days.
- **State:** SD skills effective **43**. Component system_design **43**; others BG; weighted **69**.
- **Input evidence:** none (daily run).
- **Expected skill state:** SD skills: L3, 50, MEDIUM, effective 43, label WEAK.
- **Expected gaps** (pressure GATE + FLOOR where floor > 0):

  | Skill | Tier | Raw gap | Severity | Pressure | Priority | Status | Type → focus |
  |---|---|---:|---:|---:|---:|---|---|
  | each SD T1 (8) | T1 | 37 | 37 | 13500 | **50** | HIGH | LEVEL_UP → TIMED |
  | `sd.capacity_estimation` (each T2) | T2 | 32 | 24 | 13500 | **32** | MEDIUM | LEVEL_UP → TIMED |
  | `sd.storage_search` (each T3) | T3 | 22 | 11 | 12000 | **13** | LOW | LEVEL_UP → TIMED |
  | `sd.distributed_coordination` | T4 | 7 | 1.4 | 12000 | **2** | NONE | — |

  `sd.deep_dive_bottlenecks` is **not** BLOCKED. Its prerequisite (`sd.high_level_decomposition` ≥ 60) is unsatisfied, but the skill is at L3.
- **Expected priority:** the T1 tie at 50 resolves by key: `sd.caching` (1), `sd.data_modeling` (2), `sd.database_scaling` (3), …
  - Feasibility: needed 2648 ≤ available 3060 (90 × 34), so nothing is parked.
- **Expected revision state:** no items due.
- **Expected daily plan:**
  1. `GAP sd.caching` TIMED `system_design.timed`, 50 min. Score 60 = 50 + TRACK_FLOOR 10.
  2. `GAP sd.data_modeling` TIMED `system_design.drill` (applies_to match), 20 min.

  Total 70. Focus limit reached (2 skills); `sd.database_scaling` etc. dropped `FOCUS_LIMIT`. No follow-up (20 < 30 unallocated).
- **Expected mentor message:** `READINESS_BLOCKER`: "FOUNDATION: System Design 43 < 45. Today's work targets it: sd.caching."
- **Expected readiness:** **FOUNDATION**. Blockers `[G1 "System Design 43 < 45" (deficit 2)]`. `all_failing` also includes G2 "System Design 43 < 72", G4 for all 8 SD T1 skills, and G9. `limiting_component = system_design`. A weighted 69 does not hide it.

## S03 — Weak graph pattern recognition (new topic held)

- **Given:** F0 + BG. Overrides:
  - `graph.traversal` evidence below.
  - `dsa.pattern_recognition` prior rows: 6 × `row(5,100,age∈{10,15,20,25,30,35})`.
  - `dp.fundamentals`, `dp.knapsack_subset`, `dp.strings_subsequence`, `dp.grid_paths`, `dp.interval_state_machine`, `dp.tree` are **declared unknown** (score 0, L0, LOW).
- **State:** DSA milestones DSA-1 and DSA-2 complete; current DSA milestone **DSA-3**.
- **Input evidence:** 5 unseen MEDIUM untimed attempts on fixture graph problems F101–F105 (primary `graph.traversal`, non-canonical):
  - PASS at ages 4 and 10, `pattern_identified = true`;
  - FAIL at ages 1, 3, 6, `pattern_identified = false`, mistake `WRONG_PATTERN`.
- **Expected skill state:**
  - `graph.traversal`: level **L3**, quality 40, score **51**, MEDIUM, effective **44**.
  - `dsa.pattern_recognition`: L5, quality 66.10, score **79**, HIGH, effective 79.
  - DSA component **66**.
- **Expected gaps:**
  - `graph.traversal`: raw 36, pressure 15900 (FAIL 2400 + GATE 2000 + FLOOR 1500), priority **57 HIGH**.
    - Primary PATTERN_RECOGNITION (3 of last 4 unseen misidentified) → focus PATTERN_DRILL.
    - Reasons: LARGE_GAP, BELOW_FLOOR, HIGH_IMPORTANCE, REPEATED_FAILURE, GATE_FAILING, PATTERN_MISIDENTIFIED.
  - `dp.fundamentals`: raw 80, pressure 13500, priority **100 CRITICAL**, KNOWLEDGE → LEARN. Reasons include UNLOCKS:dp.grid_paths, UNLOCKS:dp.knapsack_subset, UNLOCKS:dp.strings_subsequence.
  - `dp.knapsack_subset` / `dp.strings_subsequence` / `dp.grid_paths`: **BLOCKED** (dp.fundamentals 0 < 60), priority 76 each.
  - `dp.tree`: BLOCKED, 12. `dp.interval_state_machine`: BLOCKED (dp.fundamentals 0 < 60, level L0), 12.
  - `dsa.pattern_recognition`: priority 1, NONE.
- **Expected priority:** `dp.fundamentals` ranks 1st (100) but is a **held** LEARN candidate. `graph.traversal` ranks 2nd and is the top schedulable gap.
- **Expected revision state:** the 3 FAILs created `PROBLEM:F103` (attempt age 1 → due 11-02, today), `PROBLEM:F102` (age 3 → due 10-31, overdue 2) and `PROBLEM:F101` (age 6 → due 10-28, overdue 5). All index 0, `needs_reinforcement = true`, 35 min each (25 + 10). The clean, non-canonical passes created no items.
- **Expected daily plan:**
  1. `REV PROBLEM:F101` (`revision.reinforce`), 35 min, score 85 = 60 + 5 + 20.
  2. `GAP graph.traversal` PATTERN_DRILL `dsa.pattern_drill`, 25 min, score 57. Statements: 2 unseen primary `graph.traversal` (#28 `clone-graph`, #29 `number-of-connected-components-in-an-undirected-graph`) + 3 other-pattern statements per picker.

  Total 60. Dropped:
  - `REV PROBLEM:F102` and `REV PROBLEM:F103`: `PER_SKILL_LIMIT`.
  - `GAP dp.fundamentals`: `NEW_TOPIC_HOLD`.

  No follow-up: `dsa.independent` (35) > 30 unallocated.
- **Expected mentor message:** `NEW_TOPIC_HOLD`: "Do not start dp.fundamentals today. graph.traversal PATTERN_RECOGNITION is HIGH (57): 3 of your last 4 unseen graph.traversal problems used the wrong approach."
- **Expected readiness:** **FOUNDATION**. Blockers `[G1 dp.fundamentals level L0 < L3]`. Weighted 73.

## S04 — Retention decay

- **Given:** F0 + BG. Override `binary_search.boundaries` (T2) rows: `row(4,100,130,a)`, `row(4,100,135,b)`, `row(3,100,140,c)`; last practiced 130 days ago. Revision item `PATTERN:binary_search.boundaries` is GRADUATED (2026-06-20), with its maintenance check due 2026-10-18.
- **Input evidence:** none.
- **Expected skill state:** level **L1** (old rows qualify L1 only), quality 100, score **30**, LOW (no rows ≤ 120 days), effective **15**. Peak score **72**.
- **Expected gaps:** raw 60, severity 45, pressure 12500 (FLOOR 1500 + RETENTION 1000), priority **56 HIGH**. Primary RETENTION (peak − score = 42 ≥ 15, 130 ≥ 21 days) → REINFORCE. Reasons include DECAYED, RETENTION_RISK, BELOW_FLOOR. DSA component 74 (passes).
- **Expected priority:** rank 1.
- **Expected revision state:** maintenance check due, candidate score 45 = 30 + 15.
- **Expected daily plan:**
  1. `GAP binary_search.boundaries` REINFORCE `dsa.reinforce`, 30 min, canonical problem #16 `search-in-rotated-sorted-array`.
  2. `REV PATTERN:binary_search.boundaries` (maintenance), 10 min.

  Total 40. No follow-up (`next_on_pass = GAP_ENGINE`).
- **Expected mentor message:** `DEFAULT`: "Top priority: binary_search.boundaries (HIGH, 56): RETENTION. Peak 72, now 30; last practiced 130 days ago."
- **Expected readiness:** DEVELOPING, blockers `[G9]`.

## S05 — Repeated failure (leech)

- **Given:** F0 + BG. `db.isolation_mvcc` (T2) has revision item `CS:db.isolation_mvcc`: ACTIVE, index 0, lapses 2, `needs_reinforcement`, due 2026-11-01.
- **Input evidence:**
  - Prior rows: `row(3,80,41,pa)`, `row(3,75,36,pb)`, `row(3,45,16,pc)`, `row(3,30,9,pc)`.
  - New (yesterday, the linked revision review): `CONCEPT_EXPLAIN`, no notes, 40 points → `row(3,40,1,pc)`, review outcome **FAIL**.
- **Expected skill state:** L3, quality 52.5, score **53**, MEDIUM (5 rows, 3 sources), effective **46**. Peak 53.
- **Expected revision state:** lapses **3** → `SUSPENDED` (LEECH). The gap engine adds REPEATED_FAILURE. Reactivation happens on the first later row with level ≥ L2 and ≥ 70 points.
- **Expected gaps:** raw 29, severity 21.75, pressure 13900 (FAIL 2400 + FLOOR 1500), priority **30 MEDIUM**. Primary LEVEL_UP (L3 → TIMED). CS component 73.
- **Expected priority:** rank 1 (only gap).
- **Expected daily plan** (leech override → GUIDED):
  1. `GAP db.isolation_mvcc` GUIDED `cs.guided`, 20 min.
  2. Focus follow-up `cs.independent`, 20 min.

  Total 40.
- **Expected mentor message:** `LEECH_RELEARN`: "You failed the db.isolation_mvcc revision 3 times. Stop re-reading; re-learn it with guided practice today."
- **Expected readiness:** DEVELOPING, blockers `[G9]`. G7 pass rate 17/21 = 80%.

## S06 — High self-confidence, poor evidence

- **Given:** F0 + BG. `sliding_window.core` (T1) attempts on fixture problems F201–F206 (non-canonical), with `pattern_identified = true`:
  - `row(3,100,20)` and `row(3,100,25)` (self-rating 3);
  - FAILs `row(3,0,2)`, `row(3,0,5)`, `row(3,0,9)` with `self_rating_before` 5, 4, 5;
  - PARTIAL `row(3,50,12)` with `self_rating_before` 4.
- **Input evidence:** as above (already recorded).
- **Expected skill state:** L3, quality 41.67, score **51**, MEDIUM (span 1 level), effective **44**. Self-ratings do not change any of these values.
- **Expected gaps:** raw 36, pressure 13900 (FAIL 2400 [4 of last 5 < 60] + FLOOR 1500), priority **50 HIGH**. Primary **CONFIDENCE** (3 rows with self ≥ 4 and < 50 points) → INDEPENDENT. Reasons include OVERCONFIDENT. DSA component 74.
- **Expected revision state:**
  - FAILs → `PROBLEM:F203` (due 11-01), `F204` (10-29), `F205` (10-25): index 0, reinforcement.
  - PARTIAL → `PROBLEM:F206`: index 1, due 10-24 (overdue 9), 25 min, score 89.
- **Expected daily plan:**
  1. `REV PROBLEM:F206`, 25 min.
  2. `GAP sliding_window.core` INDEPENDENT `dsa.independent`, 35 min (closed-book).

  Total 60. Other revisions: `PER_SKILL_LIMIT`. No follow-up (`dsa.timed` 40 > 30).
- **Expected mentor message:** `OVERCONFIDENT`: "You rated yourself ≥ 4 before 3 attempts on sliding_window.core that you failed. Today is a closed-book check."
- **Expected readiness:** DEVELOPING. Blockers `[G4 "sliding_window.core effective 44 < 65 / sliding_window.core level L3 < L4", G7 "overdue T1/T2 > 7 days: 2" (F205 8 days, F206 9 days), G9]`.

## S07 — Low self-confidence, strong evidence

- **Given:** F0 + BG. `heap.top_k` (T1) rows: three unseen timed PASSes within limit, explanation 6/10 → `row(4,100,3)`, `row(4,100,6)`, `row(4,100,10)`. Self-ratings before: 2, 1, 2. Non-canonical, fast.
- **Expected skill state:** L4, quality 100, score **72**, MEDIUM, effective **65**. Identical if every self-rating were 5.
- **Expected gaps:** raw 15, pressure 10000, priority **15 LOW**. DEPTH does not match (mean depth 60 is not < 60), so primary LEVEL_UP (L4 → EXPLAIN). Reason UNDERCONFIDENT.
- **Expected priority:** rank 1.
- **Expected revision state:** no items (clean, fast, non-canonical).
- **Expected daily plan:**
  1. `GAP heap.top_k` EXPLAIN `dsa.explain`, 40 min.
  2. Follow-up `dsa.transfer`, 50 min.

  Total 90.
- **Expected mentor message:** `UNDERCONFIDENT`: "Your evidence on heap.top_k (L4, score 72) is stronger than your self-ratings (2, 1, 2). Trust it and push to EXPLAIN."
- **Expected readiness:** DEVELOPING, blockers `[G9]` (G4 passes: 65 ≥ 65 and L4).

## S08 — Speed gap

- **Given:** F0 + BG. `binary_search.basic` (T1): three unseen MEDIUM PASSes, no hints, untimed, times 48 / 41 / 52 min (expected 30): `row(3,100,3)`, `row(3,100,7)`, `row(3,100,11)`. Non-canonical.
- **Expected skill state:** L3, score **60**, MEDIUM, effective **53**.
- **Expected gaps:** raw 27, pressure 11500 (FLOOR), priority **31 MEDIUM**. Primary **SPEED** (median ratio 16000 > 12500) → TIMED. Reason SPEED_BELOW_TARGET.
- **Expected revision state:** slow clean passes create `PROBLEM` items at index 1 (+3 days): due 11-02 (score 70), 10-29 (84), 10-25 (88), 25 min each.
- **Expected daily plan:**
  1. `REV` (due 10-25), 25 min.
  2. `GAP binary_search.basic` TIMED `dsa.timed`, 40 min.

  Total 65. No follow-up (25 < 30).
- **Expected mentor message:** `SWITCH_TO_TIMED`: "You solve binary_search.basic independently (L3), but median time is 160% of target. Switch from learning to timed practice."
- **Expected readiness:** DEVELOPING. Blockers `[G4 "binary_search.basic effective 53 < 65 / binary_search.basic level L3 < L4", G7 "overdue T1/T2 > 7 days: 1" (due 10-25), G9]`.

## S09 — Communication gap

- **Given:** F0 + BG. `trees.traversal` (T1): three timed PASSes within limit, explanation 6, `execution_rubric.think_aloud` 4 / 5 / 5.
- **Input evidence:** these attempts produce `trees.traversal` rows `row(4,100,{2,5,8})` and derived `execution.think_aloud` rows `row(4,{40,50,50},{2,5,8})`.
- **Expected skill state:**
  - `trees.traversal`: L4, score 72, MEDIUM, effective 65.
  - `execution.think_aloud`: no qualifying row → L0, quality 46.67, score **5**, MEDIUM, effective **0**.
  - Components: coding **67**, dsa 75.
- **Expected gaps:**
  - `execution.think_aloud` (T2): raw 75, pressure 15900 (FAIL 2400 [all 3 rows < 60] + GATE + FLOOR), priority **89 CRITICAL** (corrected by D-061; was 13500 / 76). Communication skill, so primary COMMUNICATION (rule b), not KNOWLEDGE → THINK_ALOUD.
  - `trees.traversal`: priority **15 LOW**. Primary COMMUNICATION (rule a: comm mean 46.7 < 60 while outcome 100) → THINK_ALOUD.
- **Expected revision state:** no items.
- **Expected daily plan:**
  1. `GAP execution.think_aloud` `coding.think_aloud`, 40 min.
  2. `GAP trees.traversal` `generic.think_aloud`, 30 min (no dsa THINK_ALOUD template → generic).

  Total 70. No follow-up.
- **Expected mentor message:** `COMMUNICATION_GAP`: "Your solutions are correct, but your explanation scores average 47/100. Practice out loud, recorded."
- **Expected readiness:** DEVELOPING. Blockers `[G2 "Coding & Execution 67 < 70", G5 execution.think_aloud CRITICAL, G9]`.

## S10 — Prerequisite blocking

- **Given:** F0 + BG. Overrides: `dp.fundamentals` L1, score 25, MEDIUM (effective 18). `recursion.fundamentals` L3, score 50, MEDIUM (effective 43). No revision items due.
- **Expected skill state:** as given. DSA component **72** (passes G2 exactly).
- **Expected gaps:**
  - `dp.fundamentals`: raw 62, pressure 11500 (FLOOR), priority **71**, status **BLOCKED** (recursion 50 < 60, dp level L1 ≤ L2). Primary PREREQUISITE, `blocked_by [{recursion.fundamentals, 50, 60}]`.
  - `recursion.fundamentals`: own priority 43. Unlock max(43, round(71 × 0.9 = 63.9)) = **64 → CRITICAL**, reason UNLOCKS:dp.fundamentals. Primary LEVEL_UP → TIMED.
  - `backtracking.core` (needs recursion ≥ 60) is at L5, so **not** blocked.
- **Expected priority:** `recursion.fundamentals` rank 1; `dp.fundamentals` in the BLOCKED group.
- **Expected revision state:** none due.
- **Expected daily plan:**
  1. `GAP recursion.fundamentals` TIMED `dsa.timed`, 40 min.
  2. Follow-up `dsa.explain`, 40 min.

  Total 80.
- **Expected mentor message:** `PREREQUISITE_UNLOCK`: "Do not start dp.fundamentals yet. recursion.fundamentals (50/60) blocks it, so fix it first."
- **Expected readiness:** **FOUNDATION**. Blockers `[G1 dp.fundamentals level L1 < L3]`.

## S11 — Overdue revision overload

- **Given:** F0 + BG, except revisions. ACTIVE overdue items, all with lapses 0 and distinct item keys from real seed skills:

  | Group | Items | Minutes | Due | Score |
  |---|---|---:|---|---:|
  | T1 canonical PROBLEM items, one per skill | #15 `binary-search` (EASY, 15), #20 `maximum-depth-of-binary-tree` (EASY, 15), #27, #3, #4, #6 (MEDIUM, 25 each) | 130 | 10-08 | 100 |
  | T2 PROBLEM items | #9, #12, #16 (MEDIUM, 25 each), #22 (EASY, 15; seed difficulty, D-065) | 90 | 10-10 | 95 |
  | T2 CS items (all 10 T2 `cs` skills, 2 per day) | `CS:<skill>` | 100 | 10-20 … 10-24 | 88 … 84 |
  | T2 CONCEPT items | `python.core_syntax`, `python.collections`, `lld.design_patterns`, `lld.extensibility`, `engineering.debugging` | 50 | 10-22 | |
  | T3 SD items (all 5 T3 `system_design` skills) | `SD:<skill>`, 20 each | 100 | 10-18 | |
  | T3 CS items (all 7 T3 `cs` skills) | `CS:<skill>`, 10 each | 70 | 10-19 | |

  Backlog **540** min (D-065: was 550 with #22 taken as MEDIUM). Cap = 36.
- **Input evidence:** none.
- **Expected revision state:** triage (540 > 14 × 36 = 504). Suspend in order (lowest importance → fewest lapses → latest due → key asc) until ≤ 252:
  1. 7 T3 CS items (due 10-19) → 470;
  2. 5 T3 SD items (10-18) → 370;
  3. T2 items, latest due first: CS 10-24 ×2 → 350; CS 10-23 ×2 → 330; due 10-22: 5 CONCEPT items (key `CONCEPT:` < `CS:`) → 280, then CS ×2 → 260; the first CS item due 10-21 → 250 (≤ 252, stop).

  Result: **24** `BACKLOG_TRIAGE` actions + audit events (D-065). Remaining backlog **250** (6 T1 + 4 T2 problems + the 2 CS items due 10-20 + 1 CS item due 10-21).
- **Expected skill state / gaps:** unchanged. Skills with overdue ACTIVE items get reason OVERDUE_REVISION; statuses NONE.
- **Expected priority:** no actionable gaps.
- **Expected daily plan:** there are no non-revision candidates, so the cap is lifted:
  1. `REV PROBLEM:15`, 15 min.
  2. `REV PROBLEM:20`, 15 min.
  3. `REV PROBLEM:27`, 25 min.
  4. `REV PROBLEM:3`, 25 min.
  5. the earlier-keyed of the two CS items due 10-20 (score 60 + 13 + 15 = 88), 10 min.

  Total 90. Ties sort by key string. `PROBLEM:4`, `PROBLEM:6` and the T2 problems are dropped `BUDGET`.
- **Expected mentor message:** `BACKLOG_OVER_BUDGET`: "Revision backlog is 250 min, more than a day's budget. Revisions are limited to 36 min/day when other work exists; 24 low-importance items were suspended."
- **Expected readiness:** DEVELOPING. Blockers `[G7 "overdue T1/T2 > 7 days: 13", G9]`. ACTIVE only: 6 + 4 + 3; suspended items are not counted.

## S12 — Target date approaching (infeasible)

- **Given:** F0 + BG, `target_date = 2027-01-11` (10.0 weeks, **CONSOLIDATE**). All 6 `lld` skills at L2, score 35, LOW (effective **20**).
- **Expected skill state:** as given. LLD component **20**; weighted 68.
- **Expected gaps:**
  - `lld.requirements_entities`: priority **81 CRITICAL** (raw 60, GATE + FLOOR), PRACTICE → INDEPENDENT. Reasons include UNLOCKS:lld.class_design.
  - `lld.class_design`: BLOCKED (requirements 35 < 45), 81.
  - `lld.machine_coding`: BLOCKED (class_design 35 < 60), 81.
  - Feasibility: needed 1675 > available 750 (75 × 10). Park `lld.concurrency_safety` (T3), then `lld.design_patterns`, then `lld.extensibility` (T2, key asc) as NOT_FEASIBLE. Remaining T1 need 900 > 750 → `infeasible_components = [lld]`.
- **Expected priority:** `lld.requirements_entities` rank 1.
- **Expected revision state:** none due.
- **Expected daily plan:** `GAP lld.requirements_entities` INDEPENDENT `lld.independent`, 60 min. Total 60. No follow-up (`lld.timed` 60 > 30).
- **Expected mentor message:** `DEADLINE_INFEASIBLE`: "At the current pace LLD / OOD cannot reach target by 2027-01-11 (needs 900 min, 750 available). Only critical skills are scheduled there; consider moving the date."
- **Expected readiness:** **FOUNDATION**. Blockers `[G1 "LLD / OOD 20 < 45", G1 "lld.class_design level L2 < L3", G1 "lld.machine_coding level L2 < L3", G1 "lld.requirements_entities level L2 < L3"]`.

## S13 — BUILD phase: one new topic per day

- **Given:** F0 + BG (BUILD). Declared unknown: `trie.core` (T3, milestone DSA-3) and `os.memory_virtual` (T3, milestone CS-2). Both milestones are current; no HIGH/CRITICAL gaps in either track.
- **Expected skill state:** both score 0, L0, LOW. DSA 75, CS 73.
- **Expected gaps:** both raw 65, severity 32.5, priority **33 MEDIUM**, KNOWLEDGE → LEARN.
- **Expected priority:** tie → key asc: `os.memory_virtual` (1), `trie.core` (2).
- **Expected revision state:** none.
- **Expected daily plan:**
  1. `GAP os.memory_virtual` LEARN `cs.learn`, 40 min.
  2. Follow-up `cs.guided`, 20 min.

  Total 60. `GAP trie.core` dropped with `NEW_TOPIC_LIMIT`.
- **Expected mentor message:** `DEFAULT`: "Top priority: os.memory_virtual (MEDIUM, 33): KNOWLEDGE. Declared unknown, new topic in milestone CS-2."
- **Expected readiness:** DEVELOPING, blockers `[G9]`.

## S14 — CONSOLIDATE phase

- **Given:** F0 + BG, `target_date = 2027-01-11` (CONSOLIDATE). Overrides:
  - `trie.core` declared unknown, with a 45-min `STUDY_SESSION` on it 3 days ago;
  - `sd.storage_search` (T3) L2, effective 30;
  - mocks: last round 8 days ago (DSA 10-25), SYSTEM_DESIGN latest 10-20 (oldest).
- **Expected skill state:** as given. DSA 75, SD 75.
- **Expected gaps:**
  - all 10 T4 skills and `trie.core` → **PARKED** (PARKED_DEADLINE);
  - `sd.storage_search` priority **18 LOW** (PRACTICE → INDEPENDENT);
  - feasibility passes.
- **Expected priority:** `sd.storage_search` rank 1 actionable.
- **Expected revision state:** none due.
- **Expected daily plan:**
  1. `MOCK` SYSTEM_DESIGN `mock.round`, 60 min, score 55.

  `GAP sd.storage_search` (`system_design.independent`, 60) doesn't fit. Total 60.
- **Expected mentor message:** `STOP_STUDYING`: "Stop trie.core: parked until after 2027-01-11 (CONSOLIDATE). Move that time to sd.storage_search."
- **Expected readiness:** DEVELOPING, blockers `[G9]`. Stop list: 11 entries.

## S15 — SHARPEN phase

- **Given:** F0 + BG, `target_date = 2026-11-23` (3.0 weeks, **SHARPEN**). Overrides:
  - `heap.two_heaps_merge_k` (T3) L2, effective 25;
  - `graph.shortest_path` (T2) L1, effective 10;
  - `execution.time_management` (T2) L4, score 66, MEDIUM, effective 59;
  - mocks: last round 4 days ago (DSA 10-29); BEHAVIORAL latest 10-15 (oldest);
  - no practice minutes in the last 7 days on any parked skill (so STOP_STUDYING does not fire).
- **Expected skill state:** as given. DSA 73, coding 72.
- **Expected gaps:**
  - PARKED: all T4, `heap.two_heaps_merge_k` (T3 < L3), `graph.shortest_path` (T2 ≤ L1).
  - `execution.time_management`: priority **12 LOW**, LEVEL_UP → EXPLAIN.
- **Expected revision state:** none due.
- **Expected daily plan:**
  1. `MOCK` BEHAVIORAL `mock.round`, 45 min, score 55 (SHARPEN spacing ≥ 3 days).
  2. `GAP execution.time_management` EXPLAIN `coding.execution_drill`, 40 min.

  Total 85. No LEARN items allowed.
- **Expected mentor message:** `SHARPEN_FOCUS`: "3 weeks left. No new topics. Sharpen execution.time_management and keep mocks going."
- **Expected readiness:** DEVELOPING, `simulation_eligible = true`, blockers `[G9]`. No final simulation is scheduled (budget 90 < 160).

## S16 — Parked topic still counts and stays quiet

- **Given:** F0 + BG, `target_date = 2027-01-11` (CONSOLIDATE). Overrides:
  - `db.nosql_tradeoffs` (T3) L1, score 20, LOW (effective 5), with 60 study minutes in the last 7 days;
  - T4 `sd.distributed_coordination` has an ACTIVE revision item `SD:sd.distributed_coordination`, overdue 10 days;
  - mocks: last round 9 days ago; CS latest 10-14 (oldest).
- **Expected skill state:** as given. CS component **73**: the parked skill still counts at effective 5.
- **Expected gaps:** `db.nosql_tradeoffs` → PARKED (T3, level ≤ L1); all T4 → PARKED. No actionable assessed gaps.
- **Expected revision state:** the overdue item for a parked skill is unchanged but **not scheduled**, not in backlog (backlog 0), and not counted in G7.
- **Expected daily plan:** `MOCK` CS `mock.round`, 45 min. Total 45.
- **Expected mentor message:** `STOP_STUDYING`: "Stop db.nosql_tradeoffs: parked until after 2027-01-11 (CONSOLIDATE). Move that time to today's plan."
- **Expected readiness:** DEVELOPING, blockers `[G9]`.

## S17 — Mock weakness

- **Given:** F0 + BG + M-OK.
  - `sd.capacity_estimation` prior rows: `row(5,100,10)`, `row(5,100,20)`, `row(4,100,30)`, `row(4,100,40)`, `row(3,100,50)`, `row(4,60,25)` → score 81, HIGH.
  - `sd.caching` prior rows: `row(5,100,{8,16,24})`, `row(4,100,{32,40})`, `row(3,100,50)` → score 82, HIGH.
- **Input evidence:** PEER mock on 2026-11-01, one SYSTEM_DESIGN round, `round_score` **58**. Skill outcomes (only these two recorded):
  - `sd.capacity_estimation` 40 (weakness);
  - `sd.caching` 55 (weakness).
- **Expected skill state:**
  - `sd.capacity_estimation`: pre-cap L5 score 80. **Interview reality cap** → score **40**, HIGH, effective **40**. Level stays L5.
  - `sd.caching`: pre-cap 81 → cap **55**, effective **55**.
  - SD component 73.
- **Expected gaps:**
  - `sd.capacity_estimation`: raw 35, pressure 13000 (MOCK 1500 + FLOOR 1500), priority **34 MEDIUM**.
  - `sd.caching`: raw 25, pressure 13000, priority **33 MEDIUM**.
  - Both primary **INTERVIEW_EXECUTION** → SIMULATE. Reasons MOCK_WEAKNESS, BELOW_FLOOR.
- **Expected priority:** capacity (1), caching (2).
- **Expected revision state:** `MOCKW:<round>:sd.capacity_estimation` and `MOCKW:<round>:sd.caching` created, index 0, due **2026-11-03** (+2). Not due today.
- **Expected daily plan:** `GAP sd.capacity_estimation` SIMULATE `system_design.simulate`, 50 min. `sd.caching` (50) doesn't fit. Total 50.
- **Expected mentor message:** `MOCK_GAP`: "sd.capacity_estimation: practice level L5, but your last mock scored 40. Practice under interview conditions."
- **Expected readiness:** DEVELOPING. Blockers `[G4 "sd.caching effective 55 < 65", G6 "SYSTEM_DESIGN latest round 58 < 65", G9]`. Last-6 mean 73 and last-3 floor still pass. `simulation_eligible = false`.

## S18 — Behavioral weakness

- **Given:** F0 + BG. `behavioral.ownership`, `behavioral.impact` and `communication.structured_answers` (all T1) at L2, score 40, MEDIUM (effective **33**). The behavioral_project track got 10 min in the last 7 days. No story revisions due.
- **Expected skill state:** as given. Behavioral component **59**; weighted 74.
- **Expected gaps:** each raw 47, pressure 13500, priority **63 CRITICAL**, PRACTICE (L2) → INDEPENDENT. `communication.structured_answers` matches PRACTICE before COMMUNICATION.
- **Expected priority:** tie → key asc: `behavioral.impact`, `behavioral.ownership`, `communication.structured_answers`.
- **Expected revision state:** none due.
- **Expected daily plan:**
  1. `GAP behavioral.impact` INDEPENDENT `behavioral.independent`, 15 min. Score 73 = 63 + TRACK_FLOOR.
  2. `GAP behavioral.ownership` INDEPENDENT, 15 min.
  3. Follow-up `behavioral.timed` on `behavioral.impact`, 15 min.

  Total 45. `communication.structured_answers` dropped with `FOCUS_LIMIT`.
- **Expected mentor message:** `READINESS_BLOCKER`: "FOUNDATION: behavioral.impact level L2 < L3. Today's work targets it: behavioral.impact."
- **Expected readiness:** **FOUNDATION**. Blockers `[G1 behavioral.impact L2 < L3, G1 behavioral.ownership L2 < L3, G1 communication.structured_answers L2 < L3]`. `all_failing` adds G2 behavioral 59 < 70, G4 ×3, G5 ×3, G9.

## S19 — Final simulation failure

- **Given:** F0 + BG + M-OK. Final simulations:
  - 2026-10-18: PEER, with LLD, PASS;
  - 2026-10-25: SELF, with SD, PASS.
  - `sd.deep_dive_bottlenecks` prior rows: `row(5,100,{9,19,44})`, `row(4,100,{29,35})`, `row(3,100,55)` → 82, HIGH.
- **Input evidence:** final simulation on 2026-11-01 (Sunday budget 180), PEER. Rounds: DSA 82, SYSTEM_DESIGN **66**, BEHAVIORAL 78, PROJECT_DEEP_DIVE 74, CS 80 (mean 76). SD round `sd.deep_dive_bottlenecks` = 55 (weakness).
- **Expected skill state:** `sd.deep_dive_bottlenecks` pre-cap 81 → reality cap **55**, effective 55. SD component 74.
- **Expected gaps:** `sd.deep_dive_bottlenecks`: raw 25, pressure 13000, priority **33 MEDIUM**, INTERVIEW_EXECUTION → SIMULATE.
- **Expected priority:** rank 1.
- **Expected revision state:** `MOCKW:<round>:sd.deep_dive_bottlenecks`, due 2026-11-03.
- **Expected daily plan:** `GAP sd.deep_dive_bottlenecks` SIMULATE `system_design.simulate`, 50 min. No mock (last round 1 day ago). Total 50.
- **Expected mentor message:** `MOCK_GAP`: "sd.deep_dive_bottlenecks: practice level L5, but your last mock scored 55. Practice under interview conditions."
- **Expected readiness:** DEVELOPING, `simulation_eligible = **false**` (G4 now fails). Blockers `[G4 "sd.deep_dive_bottlenecks effective 55 < 65", G9 "final simulation 2026-11-01 failed: SYSTEM_DESIGN 66 < 70"]`.
  - The simulation is valid (composition met) but fails, so the 3 most recent are not all passing.
  - G6 still passes (latest SD 66 ≥ 65; last-6 mean 76).

## S20 — Interview-ready state

- **Given:** F0 + BG + M-OK + R-OK. Final simulations, all valid and PASS:
  - 2026-10-11 PEER (LLD);
  - 2026-10-18 PEER (SD);
  - 2026-10-25 SELF (SD).

  Two revision items are due today: `CS:db.indexing` (10 min) and `PATTERN:heap.top_k` (10 min).
- **Expected skill state:** BG. Components 76/73/75/77/76/75/73; weighted **75**.
- **Expected gaps:** none actionable (all NONE).
- **Expected priority:** empty actionable list.
- **Expected revision state:** 2 due, score 70 each.
- **Expected daily plan:**
  1. `REV CS:db.indexing`, 10 min.
  2. `REV PATTERN:heap.top_k`, 10 min.

  Total 20. Unallocated 70. No invented work.
- **Expected mentor message:** `READY_MAINTAIN`: "Interview-ready. Maintain: revisions, a mock at least every 7 days, no new topics."
- **Expected readiness:** **INTERVIEW_READY**. G0–G9 pass:
  - G9: oldest of the 3 is 22 days ≤ 30, SD and LLD both covered, 2 non-SELF.
  - **Not STRONG:** components are below stretch (e.g. dsa 76 < 80), and readiness has not been sustained for 14 days.
