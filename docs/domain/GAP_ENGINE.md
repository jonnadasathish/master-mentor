# Master Mentor — Gap Engine (Spec v2, ruleset `v1`)

The gap engine answers: **what is wrong, how badly, why, and what kind of work fixes it?**

It does **not** choose missions, problems, or durations. That belongs to `MENTOR_ENGINE.md`. Terms are as defined in `GLOSSARY.md`.

## 1. Contract

```python
calculate_gaps(
    skill_states,          # from EVIDENCE_MODEL, this run
    component_scores,      # READINESS_MODEL §3, computed from the same skill states (no gap input → no cycle)
    profile,               # tiers, gates, tracks (ROLE_PROFILE)
    graph,                 # skills + prerequisites (SKILL_GRAPH), with topological order
    skill_facts,           # per skill: last-5 scoring rows, last-4 unseen pattern rows, last-3 timed rows,
                           #            depth/communication rows, last-10 self-rated rows, last mock row,
                           #            days_since_last_practice, revision lapses, familiarity
    mock_weakness_skills,  # skills flagged is_weakness in the last 3 mock rounds (any type, ≤ 60 days old)
    revision_facts,        # per skill from the revision projection of THIS run (before triage):
                           #   max_active_lapses, has_overdue_item, has_leech
    goal,                  # target_date (nullable)
    as_of_date,
) -> GapReport             # pure, deterministic, no I/O
```

## 2. Prep phase

```text
weeks_left := (target_date − as_of_date).days / 7      (Decimal; null if no target_date)
phase := BUILD        if target_date is null or weeks_left > 12
         CONSOLIDATE  if 4 < weeks_left ≤ 12
         SHARPEN      if weeks_left ≤ 4   (includes a target date in the past)
```

## 3. Base quantities (assessed skills)

```text
effective  := effective_score                         (EVIDENCE_MODEL §9)
raw_gap    := max(target − effective, 0)
severity   := raw_gap × importance / 100              (Decimal)
```

**Deadline pressure** is expressed through phase-driven parking (§8) and feasibility, not through a multiplier. A multiplier would rank every skill higher together and change nothing.

## 4. Unassessed skills (cold start and "skill without evidence")

An unassessed skill has no effective score, so it gets an **assessment priority** in place of the severity formula:

```text
downstream := number of skills that list this skill as a direct prerequisite
priority   := min(100, importance × (100 + 10 × min(downstream, 5)) / 100)     round_half_up
status     := UNASSESSED      (unless PARKED or BLOCKED, §7)
gap type   := UNASSESSED
focus      := DIAGNOSE   (LEARN is never recommended for an unassessed skill; declaring
                          familiarity NONE makes it assessed at L0 → KNOWLEDGE → LEARN)
```

**Cold start** is the state in which most skills are unassessed. The engine needs no special mode: roots are unblocked, downstream skills are BLOCKED by unassessed prerequisites (§7.2), so assessment priority flows down the graph in topological order. The mentor's Calibration Mode (`MENTOR_ENGINE.md` §3) decides how much of the day goes to diagnostics.

## 5. Pressure (assessed skills)

```text
pressure_bp := 10000
  + FAILURE      800 × min(n_fail, 3)   if n_fail ≥ 2, where n_fail = rows with outcome_points < 60
                                         among the skill's last 5 scoring rows (by observed_at desc, id desc)
  + MOCK         1500  if the skill is flagged is_weakness in any of the last 3 mock rounds
                       (all round types, by occurred_on desc then id desc, only rounds ≤ 60 days old)
  + GATE         2000  if component_score(skill.component) < gate(skill.component)
  + FLOOR        1500  if floor > 0 and effective < floor
  + RETENTION    1000  if importance ≥ 75 and days_since_last_practice > 45
pressure_bp := min(pressure_bp, 17000)

priority := min(100, round_half_up(severity × pressure_bp / 10000))
```

`days_since_last_practice` = days since the latest **scoring** row of the skill. Study sessions do not count as practice.

Recency is deliberately counted once per mechanism:
- decay of score → evidence recency weights and level windows;
- risk of forgetting a still-scored skill → the bounded RETENTION term (+1000);
- active recall → the revision engine.

## 6. Gap types (decision table, first match = primary type)

Rows are evaluated in order. The **primary** type is the first match. `gap_types` lists **all** matches, except that `LEVEL_UP` is listed only when nothing else matches.

| # | Gap type | Exact condition | Recommended focus (stage) |
|---|---|---|---|
| 1 | `UNASSESSED` | skill is unassessed |
| `DECLARED_UNKNOWN` | the skill's state comes only from a declared unknown (familiarity NONE) | `DIAGNOSE` |
| 2 | `PREREQUISITE` | status is BLOCKED (§7.2) | `PREREQUISITE` → work on `focus_skill` = the unsatisfied prerequisite with the lowest score (unassessed first), then key |
| 3 | `KNOWLEDGE` | skill is not a communication skill **and** (`level = L0`, including declared unknown, **or** `level = L1` and the skill has ≥ 2 rows with row level 1 whose 2 most recent have mean outcome < 60; fewer than 2 such rows → no match) | `LEARN` if L0, else `RECALL` |
| 4 | `RETENTION` | (`peak_score − score ≥ 15` and `days_since_last_practice ≥ 21`) **or** an active revision item of the skill has `lapses ≥ 2` | `REINFORCE` |
| 5 | `PATTERN_RECOGNITION` | `is_pattern` and `level ≥ L1` and, among the last 4 unseen attempts with this skill as primary mapping and `pattern_identified` recorded, ≥ 2 have `pattern_identified = false` | `PATTERN_DRILL` |
| 6 | `PRACTICE` | `level ∈ {L1, L2}` | `GUIDED` if L1, `INDEPENDENT` if L2 |
| 7 | `CONFIDENCE` | among the last 10 rows with `self_rating_before` recorded, ≥ 3 have `self_rating_before ≥ 4` and `outcome_points < 50` (overconfidence) | `RECALL` if level ≤ L1, else `INDEPENDENT` (closed-book verification) |
| 8 | `SPEED` | `level = L3` and, among the last 3 rows with a recorded time and `outcome_points ≥ 70`, the median of `time_seconds × 10000 / limit_seconds` > 12500 (limit = time limit, else expected minutes × 60); **or** ≥ 2 of the last 3 timed rows exceeded their limit | `TIMED` |
| 9 | `DEPTH` | `level = L4` and the mean `depth_points` of the last 3 rows that recorded depth is < 60, where `depth_points = explanation_score × 10` (attempts) or `followup_points` (assessments) | `EXPLAIN` |
| 10 | `COMMUNICATION` | (a) the last 3 rows with a communication measure (`execution_rubric.think_aloud × 10`, `communication_points`, mock rubric `communication`) have mean < 60 **and** the same rows' mean `outcome_points ≥ 70`; **or** (b) the skill is a communication skill, `level ≤ L3`, and it has ≥ 3 scoring rows | `THINK_ALOUD` (communication skill at L0 with < 3 rows → `LEARN`) |
| 11 | `INTERVIEW_EXECUTION` | the level computed without L7 rows is ≥ L4, **and** the latest mock row for the skill within 60 days has `outcome_points < 60` | `SIMULATE` |
| 12 | `EXPERIENCE` | component ∈ {`system_design`, `lld`, `project`}, `level ≥ L4`, and the skill has never had an L6 row | `TRANSFER` |
| 13 | `LEVEL_UP` | `raw_gap > 0` and nothing above matched | by level: L0 `LEARN`, L1 `GUIDED`, L2 `INDEPENDENT`, L3 `TIMED`, L4 `EXPLAIN`, L5 `TRANSFER`, L6–L7 `SIMULATE` |

**Communication skills** (fixed list, ruleset `v1`): `execution.clarification`, `execution.think_aloud`, `communication.structured_answers`, `communication.followup_handling`. Their outcome *is* a communication measure, so low scores mean a delivery gap, not missing knowledge. A communication skill at L0 with fewer than 3 scoring rows matches no row above KNOWLEDGE and falls to `LEVEL_UP` → `LEARN`.

Underconfidence does **not** create a gap type: among the last 10 self-rated rows, ≥ 3 with `self_rating_before ≤ 2` and `outcome_points ≥ 80` adds reason `UNDERCONFIDENT` (used for messages only).

## 7. Status

### 7.1 Order of determination

```text
1. PARKED      if a parking rule applies (§8)
2. BLOCKED     if a prerequisite is unsatisfied (§7.2)
3. UNASSESSED  if unassessed
4. by priority: CRITICAL ≥ 60 · HIGH 40–59 · MEDIUM 25–39 · LOW 10–24 · NONE < 10
```

Thresholds are absolute. Priority is never normalized against other skills, so "zero critical gaps" is reachable.

### 7.2 Prerequisite blocking (weak prerequisite vs weak downstream)

```text
unsatisfied(P for D) := P.score is null or P.score < min_score(D, P)
D is BLOCKED         := any unsatisfied prerequisite AND (D unassessed OR D.level ≤ L2)
```

- A **weak downstream skill whose prerequisites are fine** is ranked normally by its own priority.
- A **weak downstream skill with a weak prerequisite** is BLOCKED: it gets no missions, and its priority flows to the prerequisite.
- A downstream skill already proven at **L3+** is never blocked by its prerequisites. Independent evidence beats graph assumptions.

**Unlock propagation.** Process skills in **reverse topological order**, deepest first, so chains propagate:

```text
for each BLOCKED D, for each unsatisfied prerequisite P of D:
    P.priority := max(P.priority, D.priority × 90 / 100)        (round_half_up)
    add reason UNLOCKS:<D.key> to P
P's status is then re-derived from its new priority (rule 4), unless P is PARKED, BLOCKED or UNASSESSED.
```

`blocked_by` on D lists each unsatisfied prerequisite as `{skill, score, min_score}`. A parked skill does not propagate unlocks.

## 8. Parking (PARKED status) and feasibility

T1 skills are **never** parked. Parked skills receive no missions and no revision scheduling. They **still count** in readiness (parking never hides a weakness).

| Phase | Parked |
|---|---|
| `BUILD` | nothing by phase |
| `CONSOLIDATE` | all T4; T3 that are unassessed or `level ≤ L1` |
| `SHARPEN` | all T4; T3 unless `level ≥ L3`; T2 that are unassessed or `level ≤ L1` |

Phase parking adds reason `PARKED_DEADLINE`.

**Feasibility** (only when `target_date` is set **and** ≥ 60% of required skills are assessed; applied after phase parking):

```text
for each component c:
    track_share(c) := track_minutes(track(c)) × weight(c) / Σ weight(components of track(c))
    available(c)   := track_share(c) × weeks_left                                  (minutes)
    needed(c)      := Σ over unparked, ASSESSED required skills of c: raw_gap × MIN_PER_POINT[c]
                      (unassessed skills are excluded until measured; the estimate would be a guess)
    while needed(c) > available(c):
        park the next skill in order: tier T3 before T2 (T1 never);
        then lower importance; then larger raw_gap; then skill_key asc
        add reason NOT_FEASIBLE; recompute needed(c)
```

| `MIN_PER_POINT` (minutes of practice per score point, per skill) | dsa 6 · coding 2 · cs 3 · lld 5 · system_design 4 · behavioral 2 · project 2 |
|---|---|

These are per-skill costs *after* accounting for multi-skill observations: one SD design exercise evidences ~6 SD skills at once, one DSA problem 1–3 skills plus execution skills. They are deliberately rough, so they only park T2/T3 skills and never T1.

If only T1 skills remain and `needed > available`, nothing more is parked. The report sets `infeasible_components: [c]`, which the mentor surfaces (`DEADLINE_INFEASIBLE` message).

## 9. Reason codes

| Code | Trigger |
|---|---|
| `UNASSESSED` | skill is unassessed |
| `DECLARED_UNKNOWN` | the skill's state comes only from a declared unknown (familiarity NONE) |
| `LARGE_GAP` | `raw_gap ≥ 30` |
| `BELOW_FLOOR` | `floor > 0` and `effective < floor` |
| `HIGH_IMPORTANCE` | `importance ≥ 75` |
| `LOW_CONFIDENCE` | confidence = LOW |
| `REPEATED_FAILURE` | FAILURE pressure applied (`n_fail ≥ 2`), or the skill has a suspended leech revision item |
| `MOCK_WEAKNESS` | MOCK pressure applied |
| `GATE_FAILING` | GATE pressure applied |
| `RETENTION_RISK` | RETENTION pressure applied |
| `DECAYED` | RETENTION gap type matched |
| `PATTERN_MISIDENTIFIED` | PATTERN_RECOGNITION matched |
| `SPEED_BELOW_TARGET` | SPEED matched |
| `OVERCONFIDENT` | CONFIDENCE matched |
| `UNDERCONFIDENT` | underconfidence rule (§6) |
| `STUDIED_NOT_TESTED` | a study session for the skill in the last 14 days and no scoring row on or after its date |
| `PREREQUISITE_BLOCKED` | status BLOCKED |
| `UNLOCKS:<skill>` | received unlock propagation from `<skill>` (max 3, by that skill's priority desc, then key) |
| `PARKED_DEADLINE` | parked by phase |
| `NOT_FEASIBLE` | parked by feasibility |
| `OVERDUE_REVISION` | an active revision item of the skill is overdue |
| `OVER_TARGET` | `effective ≥ target` and confidence HIGH (used by the mentor's stop list) |

## 10. Ranking

```text
actionable := status ∈ {CRITICAL, HIGH, MEDIUM, LOW, UNASSESSED}
order      := actionable first; then NONE, BLOCKED, PARKED
within each: priority desc, importance desc, effective_score asc (null first), skill_key asc
rank       := 1..n in that order
```

"Top gaps" in the UI means the first 3 actionable **assessed** gaps. Unassessed skills appear as calibration coverage instead.

## 11. Output

```json
{
  "run_id": 812, "as_of_date": "2026-11-02", "ruleset_version": "v1",
  "phase": "BUILD", "weeks_left": "34.0", "infeasible_components": [],
  "gaps": [{
    "skill_key": "graph.traversal", "component": "dsa", "tier": "T1",
    "current_score": 51, "effective_score": 44, "level": 3, "confidence": "MEDIUM",
    "target_score": 80, "floor_score": 65, "importance": 100,
    "raw_gap": 36, "severity": "36.00", "pressure_bp": 15900, "priority": 57,
    "status": "HIGH", "rank": 1,
    "primary_gap_type": "PATTERN_RECOGNITION",
    "gap_types": ["PATTERN_RECOGNITION"],
    "reason_codes": ["LARGE_GAP", "BELOW_FLOOR", "HIGH_IMPORTANCE", "REPEATED_FAILURE",
                     "GATE_FAILING", "PATTERN_MISIDENTIFIED"],
    "blocked_by": [], "parked_reason": null,
    "recommended_focus": {"stage": "PATTERN_DRILL", "focus_skill": "graph.traversal"},
    "metrics": {"n_fail_last5": 3, "pattern_misses_last4": 3, "days_since_last_practice": 2,
                "peak_score": 51, "component_score": 58, "component_gate": 72}
  }]
}
```

Every number in `metrics` is a value the explanation text may quote. The UI never recomputes anything.

## 12. Worked examples

**G1. Weak graph pattern recognition** (state from `EVIDENCE_MODEL.md` E2; DSA component 58 < gate 72):
- raw_gap = 80 − 44 = 36; severity 36.
- Pressure: 10000 + 2400 (3 fails) + 2000 (gate) + 1500 (floor) = 15900.
- Priority = round(36 × 1.59) = **57 → HIGH**. Primary type PATTERN_RECOGNITION (level L3, so rows 3 and 6 don't match).

**G2. Large gap / low importance vs small gap / high importance** (component failing its gate for both):

| Skill | Tier | Effective | Raw gap | Severity | Pressure | Priority |
|---|---|---:|---:|---:|---:|---:|
| `trie.core` | T3 (imp 50, target 65) | 20 | 45 | 22.5 | 12000 | **27** MEDIUM |
| `heap.top_k` | T1 (imp 100, target 80) | 70 | 10 | 10 | 12000 | **12** LOW |
| `heap.top_k` (alt.) | T1 | 60 | 20 | 20 | 13500 (gate + floor) | **27** MEDIUM |

- A large gap on a supporting skill legitimately outranks a near-target critical skill.
- Once the critical skill drops below its floor, it ties and then wins on importance.
- Under CONSOLIDATE/SHARPEN, `trie.core` at L≤1 is parked outright.

**G3. Weak prerequisite vs weak downstream** (both T1, DSA failing its gate, both MEDIUM confidence, no failures):
- `dp.fundamentals`: L1, score 25, effective 18. raw_gap 62, pressure 13500 (gate + floor), priority round(62 × 1.35 = 83.7) = 84.
- It requires `recursion.fundamentals ≥ 60`. Recursion is L3, score 50, effective 43. raw_gap 37, pressure 13500, own priority round(49.95) = 50.
- dp is **BLOCKED** (unsatisfied prerequisite and level ≤ L2), `blocked_by: [{recursion.fundamentals, 50, 60}]`.
- Unlock: recursion priority = max(50, round(84 × 0.9 = 75.6)) = **76 → CRITICAL**, reasons include `UNLOCKS:dp.fundamentals`.
- The mentor works on recursion, not DP. Had dp been at L3 already, it would not be blocked.

## 13. Constants (ruleset `v1`)

| Constant | Value |
|---|---|
| Phase thresholds | BUILD > 12 weeks; CONSOLIDATE 4 < w ≤ 12; SHARPEN ≤ 4 |
| `FAILURE_BP` | 800 per failure, applied when ≥ 2 of the last 5 rows < 60, max 3 |
| `MOCK_BP` / `GATE_BP` / `FLOOR_BP` / `RETENTION_BP` | 1500 / 2000 / 1500 / 1000 |
| `RETENTION_DAYS` (pressure) | > 45, importance ≥ 75 |
| `PRESSURE_CAP_BP` | 17000 |
| Status thresholds | CRITICAL ≥ 60, HIGH 40, MEDIUM 25, LOW 10 |
| `UNLOCK_SHARE` | 90 / 100 |
| `ASSESS_DOWNSTREAM_BONUS` | +10 per direct downstream, max 5 |
| `MIN_PER_POINT` | §8 |
| Gap-type thresholds | §6 (peak drop 15, 21 days; pattern 2 of 4; speed ratio 12500; depth 60; communication 60; mock 60/60 days) |
