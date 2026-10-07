# Master Mentor — Mentor Engine (Spec v2, ruleset `v1`)

The mentor answers: **what should I do today, and why?**

It consumes the gap report, the revision projection, readiness, and the catalog, and produces one frozen Daily Plan, a Stop List, and one Mentor Message. Revision rules live in `REVISION_ENGINE.md`; mission templates live in `MISSION_LIBRARY.md`. Terms are as defined in `GLOSSARY.md`.

## 1. Contract

```python
generate_daily_plan(
    gap_report, revision_projection, readiness, skill_states,
    templates, problems, roadmap,           # catalog
    plan_history_14d,                       # plan items of the last 14 days (status, skip_reason, skill, stage)
    practice_minutes,                       # per skill per day (definition below)
    carried_over_items,                     # yesterday's DEFERRED items
    goal, profile, as_of_date,
) -> DailyPlan    # items, stop_list, message, dropped_candidates, unallocated_minutes; pure
```

## 2. Plan lifecycle

| Event | Behavior |
|---|---|
| First `GET /today` for a local date | Run a mentor run for `as_of_date`, generate the plan, persist it **frozen** (`daily_plans` + `plan_items`). |
| Observation written mid-day | A mentor run updates skill states, gaps and readiness. **The plan does not change.** |
| Explicit regenerate | Keeps DONE/SKIPPED items, discards PENDING ones, repacks with `budget − done minutes`. Increments `regenerated_count` and writes an audit event. |
| Complete | Requires a linked observation, or `no_evidence = true`, which records a `STUDY_SESSION` with the item's minutes (L0, non-scoring). The response returns before/after deltas (`API_SPEC.md`). |
| Skip | Requires `skip_reason ∈ {NO_TIME, TOO_HARD, NOT_RELEVANT, OTHER}`. A skipped revision is MISSED: no schedule change. |
| Defer | The item is re-offered tomorrow as a candidate with +5 score, once. Deferring it again drops it. |

Same inputs give the same plan. `daily_plans.input_hash` records the hash of the inputs at generation.

## 3. Modes

**Calibration Mode:** `calibration_mode := baseline battery incomplete OR assessed required skills < 60%`.

**Calibration phase (user-facing, D-080):** `COMPLETE` when every battery item is done; else `NOT_STARTED` when no item is done and no required skill is assessed; else `ENOUGH_MEASURED` when assessed required skills ≥ `CALIBRATION_MIN_ASSESSED_PCT`; else `IN_PROGRESS`. The phase only drives the UI (calibration page, roadmap availability); the planning rules above, including the diagnostic budget share, are unchanged.

**Personal roadmap (D-080):** a read-only grouping of the gap engine's output, no new scoring. Per skill: `parked` if status PARKED; `unmeasured` if not assessed; `maintain` if status NONE (at or above target); `build` if status BLOCKED, or the recommended stage is LEARN / DIAGNOSE / PREREQUISITE, or level is L0; `sharpen` if the stage is TIMED / EXPLAIN / TRANSFER / SIMULATE / THINK_ALOUD; otherwise `consolidate`. *Focus now* = the first 5 (engine rank order) of build / consolidate / sharpen that are not BLOCKED, so a weak prerequisite is worked before the skills behind it. *Health* for the current-state snapshot: parked, unknown (not assessed), strong (status NONE), critical (status CRITICAL), else developing. *Plan changed* compares the focus lists of two evaluations (today and the previous local day); nothing is reported when the earlier list was empty.

- **Baseline battery:** the ordered list of battery items in roadmap milestone `M0-BASELINE` (`seed/roadmap.yaml`). It starts with a 15-minute familiarity sweep (a `SELF_ASSESSMENT` per required skill; `NONE` = declared unknown), then multi-skill diagnostics per component.
- While the battery is incomplete:
  - due/overdue revisions are admitted first, under the normal revision cap (normally none exist at cold start);
  - then the next pending battery items **in battery order**, greedily into the remaining budget, skipping any that don't fit;
  - no other candidate types are planned.
- A battery item is **complete** when a plan item with its `battery_item_key` is DONE, or an observation recorded with that `battery_item_key` exists (backfill). A SKIPPED or DEFERRED battery item is re-offered the next day.
- Once the battery is complete but < 60% of required skills are assessed:
  - diagnostics score at 100% of priority (normally 70%);
  - diagnostics may use up to 60% of the budget with no count limit.
- **Hybrid day (D-086):** battery open **and** assessed required skills ≥ `CALIBRATION_MIN_ASSESSED_PCT` (phase `ENOUGH_MEASURED`). The plan then also contains the existing `GAP` candidates, capped at **one** GAP mission, packed first (before revisions and the battery); due revisions and the next battery items follow in their usual order and budget rules; no `DIAGNOSTIC`, `MAINTENANCE` or `MOCK` candidates; the `CALIBRATION` message rule does not fire (the normal rules choose the message). Below the threshold the battery-only plan above applies; with the battery complete the ordinary plan applies.
- Feasibility parking (`GAP_ENGINE.md` §8) is inactive until ≥ 60% of required skills are assessed.

**Prep phase behavior** (phase from `GAP_ENGINE.md` §2):

| Phase | Mentor behavior |
|---|---|
| `BUILD` | All stages allowed. At most 1 `LEARN` item per day. Mocks start once readiness ≥ `DEVELOPING`. |
| `CONSOLIDATE` | `LEARN` only for T1/T2 skills. Mock candidate when ≥ 7 days since the last mock round. Parked skills per gap engine. |
| `SHARPEN` | **No `LEARN` items.** Diagnostics only for T1/T2. Mock candidate when ≥ 3 days since the last mock round. Message rule `SHARPEN_FOCUS` is enabled. |

**PARKED behavior:** parked skills produce no candidates (gap, diagnostic, or revision). They appear on the Stop List and still count in readiness.

## 4. Candidates and the unified scoring scale

All candidates share one scale. Integer division (`//`) floors.

| Candidate type | Source | Score |
|---|---|---|
| `REVISION` (overdue) | ACTIVE item, `due_date < as_of` | `min(100, 60 + min(days_overdue, 20) + importance // 5)` |
| `REVISION` (due today) | ACTIVE item, `due_date = as_of` | `50 + importance // 5` |
| `REVISION` (maintenance) | GRADUATED T1/T2 item at its check date | `30 + importance // 5` |
| `BASELINE` | next pending baseline battery item (battery incomplete only) | battery order; admitted after due revisions, before every other type |
| `GAP` | actionable assessed gap (CRITICAL/HIGH/MEDIUM/LOW) | `priority` (+10 `CONTINUATION` if the skill's most recent DONE plan item is within 3 days) |
| `DIAGNOSTIC` | gap status UNASSESSED | `priority × 70 // 100` (calibration: `priority`) |
| `MAINTENANCE` | T1/T2 skill with `effective ≥ target`, HIGH confidence, ≥ 21 days since practice, no revision due | `20` |
| `MOCK` | readiness ≥ DEVELOPING or phase ≠ BUILD, and days since the last mock round ≥ 7 (SHARPEN: 3) | `55`. Round type = the type whose latest round is oldest (ties: loop order). |
| `FINAL_SIMULATION` | readiness `simulation_eligible` and today's budget ≥ 160 | `95` |
| Carried over | yesterday's DEFERRED item | original score + 5 (once) |

**LEARN eligibility** (a GAP candidate whose stage is `LEARN`):
1. **Roadmap order:** the skill belongs to the current milestone of its track, or an earlier one (`seed/roadmap.yaml`). Otherwise it is held with reason `HELD_BY_ROADMAP`.
2. **New-topic hold:** if the same track has an assessed gap (level ≥ L1) with status CRITICAL or HIGH that is neither BLOCKED nor PARKED, the LEARN candidate is held with reason `NEW_TOPIC_HOLD`, referencing that gap.
3. Phase rules (§3).

If both rule 1 and rule 2 hold a candidate, the recorded reason is `NEW_TOPIC_HOLD` (the actionable one). A LEARN candidate rejected only by the 1-per-day limit is dropped with `NEW_TOPIC_LIMIT`. Held and dropped candidates are reported in `dropped_candidates` with their reason; they feed message rules.

**Milestone exit (roadmap order):** a milestone is complete when every required skill listed in it has `level ≥ L3` (milestone-specific extra criteria in `seed/roadmap.yaml` must also hold). The current milestone of a track is the first incomplete one in order. If all are complete, LEARN is unrestricted by roadmap order.

## 5. Track floors

Before sorting: for each track except `mock`, if any of its components fails its G2 gate **and** `track_minutes_7d < 50%` of the track's weekly minutes, add **+10** to that track's single highest-scoring candidate (reason `TRACK_FLOOR`).

Track minutes are soft floors, not quotas. (The gap engine's feasibility check also uses them, `GAP_ENGINE.md` §8.)

**Practice minutes** (used by track floors, OVER_TARGET and STOP_STUDYING):
- An observation's minutes are `time_seconds // 60`, else `study_minutes`, else the linked plan item's `minutes`, else 0.
- Attempts attribute all of their minutes to the problem's primary skill.
- Assessments split their minutes equally across their skills (integer division; the remainder goes to the first skill by key).
- Mocks attribute each round's minutes equally across that round's skills.
- Track minutes = Σ over the track's skills, over days [as_of − 7, as_of − 1].

## 6. Ranking and budget packing

Sort candidates by:

1. score desc;
2. `due_date` asc (null last);
3. `effective_score` asc (null first);
4. importance desc;
5. last practiced asc (null first);
6. candidate key asc (`GAP:<skill>`, `REV:<item_key>`, `DIAG:<skill>`, …).

Then greedy single pass, admitting each candidate only if **all** constraints hold:

| Constraint | Rule |
|---|---|
| Budget | `allocated + minutes ≤ B` (B = today's budget from the goal; default 90) |
| Item cap | ≤ 5 items |
| Revision cap | Σ revision minutes ≤ `max(15, B × 40 // 100)`; lifted only if no non-revision candidate fits in the remaining budget |
| Focus limit | ≤ 2 distinct skills across `GAP` items |
| Diagnostics | outside calibration: ≤ 1 diagnostic item; in calibration (battery complete): no count limit, Σ diagnostic minutes ≤ `B × 60 // 100` |
| New topics | ≤ 1 `LEARN` item per day (0 in SHARPEN) |
| Per skill | at most one non-revision item (GAP / DIAGNOSTIC / MAINTENANCE) **and** at most one REVISION item per skill per day; the focus follow-up below is the only exception. Rejected candidates are dropped with `PER_SKILL_LIMIT` |
| Mock | ≤ 1 mock. If a FINAL_SIMULATION candidate exists and fits, it is admitted **first and alone**; nothing else is planned that day |

**Drop reasons** (recorded in `dropped_candidates`, one per rejected candidate, first applicable):

| Code | Meaning |
|---|---|
| `NEW_TOPIC_HOLD` | LEARN held by a HIGH/CRITICAL gap in the same track |
| `HELD_BY_ROADMAP` | LEARN skill is beyond the track's current milestone |
| `NEW_TOPIC_LIMIT` | a LEARN item is already planned (or SHARPEN) |
| `FOCUS_LIMIT` | 2 GAP skills already planned |
| `PER_SKILL_LIMIT` | the skill already has a non-revision / revision item |
| `REVISION_CAP` | the revision cap would be exceeded |
| `DIAGNOSTIC_LIMIT` | diagnostic count or calibration share reached |
| `ITEM_CAP` | 5 items already planned |
| `BUDGET` | does not fit the remaining minutes |
| `MIN_BUDGET` | template `min_budget` exceeds today's budget |
| `CONTENT_MISSING` | no template or no eligible problem |

**Focus follow-up:**
- Trigger: after the greedy pass, `unallocated ≥ 30` and the first GAP item's template has a concrete `next_on_pass` stage (not `GAP_ENGINE` / `MOCK`).
- Action: add **one** follow-up item for the same skill at that stage, if it fits (reason `FOCUS_FOLLOW_UP`). Example: a pattern drill followed by an independent solve on the same pattern.
- This deepens focus instead of spreading attention.

Remaining underfill is allowed: `unallocated_minutes` is reported, and the mentor never invents unrelated work to fill time. Item `position` is the admission order.

## 7. Stage, template and problem selection

**Stage:**
1. Start from the gap's `recommended_focus.stage`. For `PREREQUISITE`, the gap engine already redirected priority to the prerequisite, which is its own GAP candidate.
2. **Leech override:** a skill with a LEECH revision item uses `GUIDED`, or `LEARN` if level ≤ L1.
3. **Too-hard step-down:** if the skill's most recent plan item in the last 7 days was SKIPPED with `TOO_HARD`, step one stage down on the ladder `LEARN < RECALL < GUIDED < INDEPENDENT < TIMED < EXPLAIN < TRANSFER < SIMULATE`. The special stages map first: `PATTERN_DRILL → GUIDED`, `THINK_ALOUD → INDEPENDENT`, `REINFORCE → GUIDED`.
**Template selection by candidate type:**

| Candidate | Template |
|---|---|
| GAP, DIAGNOSTIC, MAINTENANCE, FOLLOW_UP | the five-level lookup in `MISSION_LIBRARY.md` §1 (component + stage, narrowed by gap type and `applies_to`, falling back to `generic`). DIAGNOSTIC uses stage DIAGNOSE; MAINTENANCE uses the stage for the skill's level (LEVEL_UP mapping) |
| REVISION | `revision.reinforce` if `needs_reinforcement`; else by item type: PROBLEM → `revision.problem`, PATTERN → `revision.pattern`, CS → `revision.cs`, CONCEPT → `revision.concept`, SD → `revision.sd`, BEHAVIORAL with key `STORY:` → `revision.story` and `PROJECT:` → `revision.project`, MOCK_WEAKNESS → `revision.mock_weakness` |
| MOCK | `mock.round` for the chosen round type; if it doesn't fit the remaining budget, `mock.prep` |
| FINAL_SIMULATION | `mock.final_simulation` |
| BASELINE | none (the battery item definition in `seed/roadmap.yaml` is the instruction) |

If no template is found, the candidate is dropped with `CONTENT_MISSING`. A template whose `min_budget` exceeds today's budget is dropped with `MIN_BUDGET`.

**Problem picker** (templates with `needs_problem`):

| Stage | Difficulty | Seen allowed? |
|---|---|---|
| DIAGNOSE (and battery DSA items) | MEDIUM (EASY for T3) | unseen only; **greedy cover**: pick problems one at a time, each maximizing the number of not-yet-covered unassessed mapped skills (battery: skills in the item's groups) |
| LEARN | EASY | unseen, or last attempt ≥ 30 days ago |
| GUIDED | EASY | unseen, or last attempt ≥ 30 days ago |
| THINK_ALOUD | MEDIUM | unseen only |
| INDEPENDENT, TIMED, EXPLAIN, SIMULATE | MEDIUM | unseen only |
| TRANSFER | HARD | unseen only |
| REINFORCE | as the canonical problem | canonical, last attempt ≥ 7 days ago |
| PATTERN_DRILL | any | 5 unseen *statements*: 2 mapped primary to the target pattern + 3 from other patterns with level ≥ L1 (for `dsa.pattern_recognition`: 5 distinct patterns) |

- This table is authoritative for difficulty. A template's `difficulty` field is documentation and a fallback for stages not listed.
- Filter on primary mapping first; if no problem passes the difficulty/seen filters, use secondary. Skills no problem maps (`execution.*`) may use any problem (D-069). A focus follow-up without a fresh problem reuses the first item's problem.
- Order: fewest total attempts, then `platform_key` asc.
- If the difficulty is unavailable, relax one step toward MEDIUM. Otherwise drop with `CONTENT_MISSING`, which the message reports as "add 3 problems for X".

## 8. Stop list (stop-learning rules)

| Entry | Condition | Instruction |
|---|---|---|
| `PARKED_DEADLINE` / `NOT_FEASIBLE` | gap status PARKED | "Stop studying X until after the target date." |
| `OVER_TARGET` | `effective ≥ target`, HIGH confidence, and the skill took > 20% of practice minutes in the last 14 days | "Maintain only; move time to the top gap." |
| `STUDIED_NOT_TESTED` | gap reason `STUDIED_NOT_TESTED` | "Stop reading X; test yourself (RECALL)." |

One entry per skill. When several conditions hold, the entry type is the first in table order (PARKED > OVER_TARGET > STUDIED_NOT_TESTED). For rules 15 and 16, the subject is the qualifying entry with the most practice minutes in the last 7 days, then skill key asc.

## 9. Mentor message rules (first match wins)

Rules are evaluated against the **plan just built**. "Top gap item" means the highest-positioned plan item of type GAP.

| # | Rule | Condition | Message template | Explanation payload |
|---|---|---|---|---|
| 1 | `CALIBRATION` | calibration mode | "Calibration: {assessed}/{required} required skills measured. Today's diagnostics: {items}. No new material until the baseline is complete." The "Today's diagnostics: {items}." sentence is omitted when no diagnostic item is in the plan (all done, skipped or deferred) | assessed, required, battery items |
| 2 | `DEADLINE_INFEASIBLE` | `infeasible_components` non-empty | "At the current pace {component} cannot reach target by {target_date} (needs {needed} min, {available} available). Only critical skills are scheduled there; consider moving the date." | needed, available |
| 3 | `READINESS_LAPSED` | readiness `lapsed` | "Readiness lapsed: {gate} failed ({actual} vs {required}). Restore it before anything else." | blocker |
| 4 | `BACKLOG_OVER_BUDGET` | triage suspended items today, or backlog > 14 × cap (D-068) | "Revision backlog is {backlog} min, more than a day's budget. Revisions are limited to {cap} min/day when other work exists; {n} low-importance items were suspended." | backlog, cap, suspended keys |
| 5 | `LEECH_RELEARN` | a planned skill has a LEECH revision item | "You failed the {skill} revision {lapses} times. Stop re-reading; re-learn it with guided practice today." | item, lapses |
| 6 | `PREREQUISITE_UNLOCK` | top gap item has `UNLOCKS:*` | "Do not start {downstream} yet. {skill} ({score}/{min_score}) blocks it, so fix it first." | blocked_by |
| 7 | `NEW_TOPIC_HOLD` | a LEARN candidate was held with `NEW_TOPIC_HOLD` | "Do not start {held_skill} today. {gap_skill} {gap_type} is {status} ({priority}): {evidence_summary}." | held skill, gap metrics |
| 8 | `SWITCH_TO_TIMED` | top gap item primary type SPEED | "You solve {skill} independently (L3), but median time is {ratio}% of target. Switch from learning to timed practice." | median ratio, last 3 times |
| 9 | `PATTERN_DRILL` | top gap item primary type PATTERN_RECOGNITION | "In {misses} of your last 4 {skill} problems you chose the wrong approach. Drill recognition before solving more." | misses |
| 10 | `COMMUNICATION_GAP` | top gap item primary type COMMUNICATION | "Your solutions are correct, but your explanation scores average {comm}/100. Practice out loud, recorded." | communication rows |
| 11 | `SUBSTEP_DRILL` | top `system_design` gap item's skill has ≥ 2 of its last 3 rows < 50 **and** the system_design component score rose ≥ 5 vs the readiness snapshot 28 days earlier | "Your system-design work is improving (+{delta}), but you keep failing {skill}. Drill {skill} instead of starting another system." | delta, rows |
| 12 | `OVERCONFIDENT` | a planned skill has primary type CONFIDENCE | "You rated yourself ≥ 4 before {n} attempts on {skill} that you failed. Today is a closed-book check." | rows |
| 13 | `UNDERCONFIDENT` | a planned skill has reason UNDERCONFIDENT | "Your evidence on {skill} (L{level}, score {score}) is stronger than your self-ratings ({ratings}). Trust it and push to {stage}." | rows |
| 14 | `MOCK_GAP` | a planned skill has primary type INTERVIEW_EXECUTION | "{skill}: practice level L{level}, but your last mock scored {mock}. Practice under interview conditions." | mock row |
| 15 | `STOP_STUDYING` | a stop-list skill had practice or study minutes in the last 7 days | "Stop {skill}: {reason}. Move that time to {top_gap or 'today's plan'}." | stop entry, minutes |
| 16 | `STUDIED_NOT_TESTED` | any stop entry `STUDIED_NOT_TESTED` | "You studied {skill} {minutes} min without testing. Reading isn't evidence; take the recall check." | study minutes |
| 17 | `SHARPEN_FOCUS` | phase SHARPEN | "{weeks} weeks left. No new topics. Sharpen {top_gap} and keep mocks going." | weeks_left |
| 18 | `MOCK_DUE` | plan contains MOCK or FINAL_SIMULATION | "Mock day: {round_type}. Simulate interview conditions; score honestly." | days since last |
| 19 | `READINESS_BLOCKER` | state FOUNDATION or DEVELOPING and the first blocker's component (a skill blocker uses its skill's component) equals the top gap item's component | "{state}: {blocker message}. Today's work targets it: {skill}." | blocker |
| 20 | `READY_MAINTAIN` | readiness ≥ INTERVIEW_READY | "Interview-ready. Maintain: revisions, a mock at least every 7 days, no new topics." | gates |
| 21 | `DEFAULT` | always | "Top priority: {skill} ({status}, {priority}): {gap_type}. {top_reason}." (No gap item: "No gaps above threshold today. Revisions and maintenance only.") | gap metrics |

Every message stores `message_rule`, `message_text`, and `message_payload_json`. Every number in the text comes from the payload.

**Placeholder rules:**
- Numbers are integers (`weeks_left` floored; means rounded half-up). Ratios are percentages.
- Components use their profile display name; skills use their key.
- `{blocker message}` is the blocker's `message` (`READINESS_MODEL.md` §8).
- `{items}` is the comma-joined battery or plan item keys.

`{top_reason}` and `{evidence_summary}` are the sentence of the first matching reason code, in this order; `{reason}` (rule 15) is the sentence of the stop entry's own code (D-068):

| Reason code | Sentence |
|---|---|
| `DECLARED_UNKNOWN` | "Declared unknown, new topic in milestone {milestone}." |
| `DECAYED` | "Peak {peak_score}, now {score}; last practiced {days_since_last_practice} days ago." |
| `PATTERN_MISIDENTIFIED` | "{misses} of your last 4 unseen {skill} problems used the wrong approach" |
| `SPEED_BELOW_TARGET` | "median time is {ratio}% of target" |
| `REPEATED_FAILURE` | "{n_fail} of your last 5 attempts failed" |
| `MOCK_WEAKNESS` | "flagged weak in a recent mock" |
| `BELOW_FLOOR` | "effective {effective} is below the floor {floor}" |
| `PARKED_DEADLINE` | "parked until after {target_date} ({phase})" |
| `NOT_FEASIBLE` | "not feasible before {target_date} at the current pace" |
| `STUDIED_NOT_TESTED` | "studied {minutes} min without a test" |
| `LARGE_GAP` | "{raw_gap} points below target" |
| (none of the above) | "{raw_gap} points below target" |

Golden scenarios assert the full text.

## 10. Weekly review

Generated lazily on the first request after the week (Monday–Sunday, local) ends. It stores metrics; the user adds a reflection.

| Metric | Definition |
|---|---|
| `active_days` | days with ≥ 1 scoring row |
| `planned_minutes` / `completed_minutes` | Σ allocated minutes of plan items / of DONE items |
| `plan_completion_pct` | completed / planned × 100 (integer, floor) |
| `revision_completion_pct` | reviews done / revision items planned |
| `minutes_by_track` | vs profile weekly minutes |
| `top_gaps` | top 5 actionable assessed gaps at week end |
| `gap_changes` | priority delta vs the start-of-week snapshot for skills in either top-5 |
| `strongest_improvement` / `biggest_regression` | largest effective-score increase / decrease |
| `readiness` | state and weighted score at start and end, new/cleared blockers |
| `mocks` | rounds and scores |
| `backlog` | revision backlog minutes at week end |
| `next_week_focus` | top 3 actionable assessed gaps, tracks below 50% allocation, stop list |

Reflection fields (free text, never read by engines): `improved`, `still_weak`, `failure_causes`, `stop_doing`, `next_priority`.

## 11. Output

```json
{
  "plan_date": "2026-11-02", "run_id": 812, "ruleset_version": "v1",
  "budget_minutes": 90, "allocated_minutes": 85, "unallocated_minutes": 5,
  "phase": "BUILD", "calibration_mode": false,
  "items": [{
    "position": 1, "candidate_type": "GAP", "skill_key": "graph.traversal",
    "template_key": "dsa.pattern_drill", "stage": "PATTERN_DRILL", "minutes": 25,
    "candidate_score": 57, "problem_ids": [101, 102, 140, 155, 160],
    "reason_codes": ["PATTERN_MISIDENTIFIED", "REPEATED_FAILURE", "BELOW_FLOOR"],
    "explanation": {"current": 51, "effective": 44, "target": 80, "priority": 57,
                    "evidence": "3 of last 4 unseen graph problems: wrong pattern",
                    "expected_outcome": "pattern drill ≥ 4/5 (L3 evidence on dsa.pattern_recognition)"}
  }],
  "stop_list": [], "dropped_candidates": [{"key": "GAP:dp.fundamentals", "reason": "NEW_TOPIC_HOLD"}],
  "message": {"rule": "NEW_TOPIC_HOLD", "text": "…", "payload": {}}
}
```

## 12. Constants (ruleset `v1`)

| Constant | Value |
|---|---|
| Calibration | battery incomplete or < 60% of required skills assessed |
| `FOCUS_FOLLOW_UP` | one extra item on the top gap skill when ≥ 30 min remain |
| Diagnostic factor | 70/100 (calibration 100/100); calibration diagnostic budget 60% |
| Revision scores | overdue `60 + min(d, 20) + imp//5` (max 100); due `50 + imp//5`; maintenance `30 + imp//5` |
| `CONTINUATION_BONUS` / window | +10 / 3 days |
| `MAINTENANCE_SCORE` | 20 (≥ 21 days since practice) |
| `MOCK_SCORE` / spacing | 55 / 7 days (SHARPEN 3) |
| `FINAL_SIM_SCORE` / min budget | 95 / 160 minutes |
| `CARRY_OVER_BONUS` | +5, once |
| `TRACK_FLOOR_BONUS` | +10 when the component fails G2 and the track got < 50% of its weekly minutes in the last 7 days |
| Packing | ≤ 5 items, revision cap 40% (min 15), focus 2 skills, 1 diagnostic, 1 LEARN, per skill 1 non-revision + 1 revision |
| Stop list | OVER_TARGET share > 20% of the last 14 days |
| `SUBSTEP_DRILL` | ≥ 2 of the last 3 rows < 50; component +5 vs 28 days earlier |
