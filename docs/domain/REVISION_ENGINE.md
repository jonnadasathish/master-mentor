# Master Mentor — Revision Engine (Spec v2, ruleset `v1`)

Revision exists to **recover memory under test conditions**, not to remind. Every review is a closed-book retrieval that produces evidence. Calendar dates only decide *when* to test, never *whether* you remember.

Terms are as defined in `GLOSSARY.md`. This document is the single owner of revision rules. `MENTOR_ENGINE.md` only schedules due items into the daily plan.

## 1. Contract

```python
project_revision_items(observations, revision_item_actions, graph, profile, as_of_date)
    -> RevisionProjection   # items with state, due_date, interval_index, lapses, needs_reinforcement
schedule_revision(item, review_outcome, review_date) -> item          # pure transition (§5)
triage_backlog(items, gap_statuses, daily_budget, as_of_date) -> [RevisionItemAction]   # §8
```

**Order inside a mentor run:**
1. evidence → skill states → component scores;
2. `project_revision_items` (replays recorded actions; never creates new ones);
3. gaps (consume revision facts);
4. **triage/auto-resume, only in the run that generates a daily plan** (the first `GET /today` of a local date). It writes action rows, then the revision projection is refreshed;
5. readiness (G7 sees post-triage items).

`/admin/rebuild` replays the recorded actions and never re-triages.

```text
revision_health(items, reviews, as_of_date) -> {overdue_t1_t2_over_7d, pass_rate_30d, reviews_30d}
```

`revision_items` is a **projection**. It is rebuilt by replaying, in date order, creation triggers (observations), reviews (observations carrying `revision_item_key`), and `revision_item_actions`. There is no separate review table. The only persisted decisions are the actions: manual suspend/resume and backlog-triage suspend/resume. These are raw rows, so a rebuild reproduces the same schedule.

## 2. Item types

| Type | Item key | Applies to | Review activity (closed-book) | Minutes | Evidence produced |
|---|---|---|---|---:|---|
| `PROBLEM` | `PROBLEM:<problem_id>` | catalog problems | Re-solve with time limit = item minutes (a known problem must be faster than a first solve) | EASY 15 · MEDIUM 25 · HARD 35 | attempt `mode=REVISION` (capped at L3 as a seen problem) |
| `PATTERN` | `PATTERN:<skill_key>` | DSA skills with `is_pattern` | Classify 5 statements (≥ 2 of this pattern), name the pattern and the key invariant | 10 | `PATTERN_DRILL` assessment |
| `CS` | `CS:<skill_key>` | component `cs` | 3 questions incl. 1 why/trade-off, answer aloud, grade against answer key | 10 | `CONCEPT_EXPLAIN` (no notes → L3, timed → L4) |
| `CONCEPT` | `CONCEPT:<skill_key>` | `python.*`, non-pattern DSA skills except `dsa.pattern_recognition`, `lld.*` except `lld.machine_coding`, `engineering.*`, `testing.*` | Explain or sketch code from memory, then check | 10 | `CONCEPT_EXPLAIN` / `CODE_EXERCISE` |
| `SD` | `SD:<skill_key>` | component `system_design` | 20-minute targeted redo: apply the building block to a fresh mini-scenario, or run the drill for an execution skill (estimation, deep dive, trade-offs) | 20 | `SD_DESIGN` / `ESTIMATION_DRILL` |
| `BEHAVIORAL` | `STORY:<story_id>` or `PROJECT:<project_key>` | stories; project walkthroughs | Timed delivery (story ≤ 3 min; walkthrough ≤ 10 min) + 2 self-probes | story 10 · project 15 | `STORY_REHEARSAL` / `PROJECT_WALKTHROUGH` |
| `MOCK_WEAKNESS` | `MOCKW:<mock_round_id>:<skill_key>` | skills flagged `is_weakness` in a mock round (max 3 per round: lowest outcome, then key) | Targeted drill from the component's DRILL template | 15 | template's observation kind |

**Item skill:** every item belongs to exactly one skill. That is the problem's primary skill for PROBLEM items, the story's first competency or `project.architecture_walkthrough` for BEHAVIORAL items, and the named skill otherwise. Importance, parking and per-skill limits use this skill.

Not revised directly: `execution.*` (practiced inside attempts), `dsa.pattern_recognition` (covered by PATTERN items), `lld.machine_coding` (90-minute missions, not reviews).

## 3. Creation triggers

| Type | Created when (first time only; an item key never duplicates) | Initial index |
|---|---|---|
| `PROBLEM` | an attempt on a **canonical** problem (any outcome), **or** on a non-canonical problem with outcome FAIL/PARTIAL, `hints_used ≥ 1`, `solution_viewed`, or time ratio > 12500 | by outcome (below) |
| `PATTERN` | first scoring row (≥ L1) on the pattern skill | 1 |
| `CS`, `CONCEPT`, `SD` | first scoring row with level ≥ L2 on the skill | by outcome |
| `BEHAVIORAL` | story created; first `PROJECT_WALKTHROUGH` assessment for a project | 0 |
| `MOCK_WEAKNESS` | mock round saved with `is_weakness` rows | 0 (MOCKW ladder) |

Initial index by the triggering row's `outcome_points` for the item's skill:

| Outcome points | Index | Due | `needs_reinforcement` |
|---|---:|---|---|
| < 50 | 0 | +1 day | true |
| 50–89, or ≥ 90 with time ratio > 12500 | 1 | +3 days | false |
| ≥ 90 | 2 | +7 days | false |

**Capacity by design:** a clean, fast, independent PASS on a non-canonical problem creates **no** problem item. The pattern item covers it. The problem catalog marks 2–3 canonical problems per pattern (`seed/problems.yaml`).

## 4. Intervals

| Ladder | Index → days |
|---|---|
| Standard (all types except MOCK_WEAKNESS) | 0→1, 1→3, 2→7, 3→14, 4→30, 5→60 |
| `MOCK_WEAKNESS` | 0→2, 1→5, 2→12 |

`due_date` is a local DATE: `review_date + interval_days`.

## 5. Outcomes

Review outcome from the linked observation:
- `PROBLEM`:
  - **PASS**: outcome PASS, `hints_used = 0`, no solution, `time_seconds ≤ item minutes × 60`.
  - **PARTIAL**: PASS with hints or slower, or outcome PARTIAL.
  - **FAIL**: outcome FAIL or `solution_viewed`.
- All other types use the item skill's outcome points: **PASS** ≥ 70 · **PARTIAL** 50–69 · **FAIL** < 50.

| Outcome | Transition |
|---|---|
| **PASS** | if index is the ladder's last → state `GRADUATED` (§7); else `index += 1`. `due = review_date + interval[index]`. `needs_reinforcement = false`. |
| **PARTIAL** | index unchanged. `due = review_date + interval[index]`. |
| **FAIL** | `lapses += 1`, `index = 0`, `needs_reinforcement = true`, `due = review_date + interval[0]`. If `lapses ≥ 3` → **Leech** (§6). |
| **MISSED** | Not an outcome and never recorded. A due item that is not reviewed (skipped or deferred plan item, or not scheduled) keeps its due date and becomes overdue. **Missing is never treated as failing.** |

**Overdue handling:**
- `due` means `due_date ≤ as_of_date`; `overdue` means `due_date < as_of_date`; `days_overdue = as_of_date − due_date`.
- Overdue items are not penalized in scheduling. A late PASS advances normally from the review date: remembering after a longer gap is stronger evidence, not weaker.
- Overdue items do get a higher mentor candidate score (`MENTOR_ENGINE.md` §4) and count toward gate G7.

**Only explicitly linked observations are reviews.** An observation counts as a review only when it is recorded with `revision_item_key`, which plan items and the Revision page set. Ad-hoc practice on the same subject is ordinary evidence and does not move the schedule.

**Reinforcement:** when `needs_reinforcement = true`, the mentor schedules the item with the `revision.reinforce` template (10-minute concept refresh, then the closed-book retry, +10 minutes). The outcome of the retry is the review outcome.

## 6. Leech (repeated failure)

When `lapses ≥ 3`:
- the item becomes `SUSPENDED` with reason `LEECH`;
- the gap engine adds `REPEATED_FAILURE` to the skill;
- the mentor forces the skill's next gap mission to stage `GUIDED`, or `LEARN` if `level ≤ L1`, regardless of gap type. Memorizing again won't fix this; re-learning will.

**Reactivation (automatic, projection rule):** the first scoring row on the skill after the suspension date with `level ≥ L2` and `outcome_points ≥ 70` reactivates the item: `ACTIVE`, index 0, `lapses = 1`, due = that row's date + 1.

## 7. Graduation and maintenance

- A PASS at the last index sets state `GRADUATED`.
- T3/T4 skills: no further reviews.
- T1/T2 skills: one **maintenance check** every 120 days (`due = graduation_or_last_check + 120`). PASS → next check +120. PARTIAL → +60. FAIL → `ACTIVE`, index 2, `lapses += 1`, `due = review_date + 7`.
- A maintenance check stays a candidate from its due date until it is reviewed (overdue checks keep the maintenance score). It never counts toward backlog or G7.

## 8. Capacity, backlog and suspension

```text
cap            := max(15, floor(daily_budget × 40 / 100))           # minutes/day for revisions
backlog        := Σ minutes of ACTIVE items with due_date ≤ as_of_date, excluding items of PARKED skills
                  (+10 per item with needs_reinforcement)
```

| Rule | Exact behavior |
|---|---|
| Daily cap | The mentor packs revision items into at most `cap` minutes. Exception: when no non-revision candidate fits, revisions may fill the budget. |
| Triage trigger | `backlog > 14 × cap` |
| Triage | Suspend (`SUSPENDED`, reason `BACKLOG_TRIAGE`) ACTIVE due items in order: lowest skill importance → fewest lapses → latest `due_date` → `item_key`. **Never T1 items.** Stop when `backlog ≤ 7 × cap`. Each suspension is a `revision_item_actions` row plus an audit event. |
| Auto-resume | When `backlog < 3 × cap` in the plan-generating run, resume up to 3 BACKLOG_TRIAGE items (highest importance → most lapses → earliest original due → key) with `due = as_of_date`. Each is an action row. |
| Parked skills | Their items keep their state but are not scheduled, not counted in backlog, and not counted in G7. They resume naturally when the skill is unparked. |
| Manual suspend/resume | User action → action row + audit. Resume sets `due = as_of_date`. |

At the default 90-minute budget: cap = 36 minutes (enough for one MEDIUM problem review with reinforcement, 35 min), triage when backlog > 504 minutes, triage stops at ≤ 252, auto-resume below 108.

## 9. Outputs for other engines

| Consumer | Fields |
|---|---|
| Gap engine | per skill: `max_active_lapses`, `has_overdue_item`, `has_leech` |
| Mentor | due/overdue items with minutes, `days_overdue`, `needs_reinforcement`, skill importance, backlog, cap, triage actions |
| Readiness (G7) | `overdue_t1_t2_over_7d`: count of **ACTIVE** items (SUSPENDED, GRADUATED and parked-skill items excluded) of T1/T2 skills with `days_overdue > 7`; `pass_rate_30d` = `100 × PASS // reviews` over reviews in the last 30 days (integer floor; PARTIAL is not a pass); `reviews_30d` |

## 10. Constants (ruleset `v1`)

| Constant | Value |
|---|---|
| `STANDARD_INTERVALS` | [1, 3, 7, 14, 30, 60] |
| `MOCKW_INTERVALS` | [2, 5, 12] |
| `LEECH_LAPSES` | 3 |
| `MAINTENANCE_DAYS` | 120 (PARTIAL: 60) |
| `REVISION_CAP_PCT` / min | 40% / 15 minutes |
| Triage | trigger 14 × cap, target 7 × cap, resume below 3 × cap, max 3 resumes/day |
| `REINFORCE_EXTRA_MINUTES` | 10 |
| Pass thresholds | ≥ 70 PASS, 50–69 PARTIAL, < 50 FAIL; PROBLEM time ≤ item minutes |
| Initial index | < 50 → 0; 50–89 or slow → 1; ≥ 90 → 2; PATTERN → 1; BEHAVIORAL → 0 |
