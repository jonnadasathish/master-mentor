# Master Mentor — Evidence Model (Spec v2, ruleset `v1`)

Evidence answers one question: **what can the candidate demonstrably do?**

Terms are as defined in [`GLOSSARY.md`](GLOSSARY.md). Constants are collected in §13 and implemented in `backend/app/domain/rulesets/v1.py`.

## 1. Principles

1. **Observations are authoritative; evidence is derived.** Attempts, assessments, revision reviews and mock rounds are append-only raw records. `evidence` rows are a deterministic projection of them, rebuilt per ruleset version.
2. **Self-rating never contributes to score, level, or confidence.** It is stored for the CONFIDENCE gap type and messages only.
3. **Asymmetric self-report.** A user may lower their state by declaring a skill unknown (§5.7). A user can never raise it by self-report. The Starting Profile's self-reported strengths and weaknesses (D-080) are not even that: they are stored apart (`starting_profile`), read by no engine, and shown beside measured values as "not yet verified".
4. **Levels, not averages, define what is proven.** A skill's score is bounded by the highest evidence level it has *qualified* for. Many easy wins cannot produce a high score.
5. **Integer/Decimal arithmetic only.** No floats (§11).

## 2. Pipeline

```text
Observation (raw, append-only)
  → derivation rules (§5)          → evidence rows: (skill, level, outcome_points, weights, source_key)
  → per-skill qualification (§7.1) → level
  → quality (§7.2)                 → score (§7.3)
  → confidence (§8)                → effective_score (§9), label (§10)
```

Every evidence row carries `ruleset_version`. Changing any rule here requires a new ruleset version and a rebuild.

## 3. The evidence ladder (L0–L7)

| Level | Name | Exact meaning | Required evidence (one row) | Examples | Score band | Confidence contribution | Does **NOT** prove |
|---|---|---|---|---|---|---|---|
| **L0** | Exposed | You spent time on it. | Study session, self-assessment, or a failed/unqualified attempt | Read the B-tree chapter; watched a sliding-window video; self-rated 4/5 | 0–10 (only if scoring rows exist and none qualify) | none (study and self-assessment rows are not scoring rows) | that you can recall, solve, or explain anything |
| **L1** | Recall | You can retrieve the idea closed-book. | Closed-book recall quiz or pattern classification ≥ 60, or a seen problem re-solved within 7 days | Recall quiz "4 isolation levels + anomalies" 8/10 | 10–30 | counts | that you can apply it to a new problem |
| **L2** | Guided | You can solve or produce it with help. | Practice with hints, notes, or reference; or after viewing a solution | Solved with 1 hint; explained MVCC using notes | 30–45 | counts | independent ability |
| **L3** | Independent | You solve or produce it alone, untimed. | Unseen problem PASS, no hints, no solution; or practice without notes | Unseen medium solved in 48 min, no hints | 45–60 | counts | speed, explanation quality, transfer |
| **L4** | Timed | L3 within the interview time limit. | L3 + `timed` + `time_seconds ≤ time_limit_seconds` + MEDIUM/HARD (problems) | Medium in 26 min with a 30-minute timer | 60–72 | counts | you can explain trade-offs or handle follow-ups |
| **L5** | Explain | L4 plus correct reasoning out loud. | L4 + explanation ≥ 7/10 + correct complexity (problems), or follow-up/trade-off rubric ≥ 70 (assessments) | Timed solve, stated O(n log n) correctly, justified the heap | 72–82 | counts | transfer to unfamiliar variants or real systems |
| **L6** | Transfer | Ability holds on harder or unfamiliar ground. | L5 + (HARD difficulty or follow-up variant solved) for problems; L5 + (peer-evaluated or unseen-variant prompt), or an applied task with follow-up ≥ 70, for assessments | Solved a follow-up "now stream the input"; applied rate limiting in a real service and defended it | 82–90 | counts | performance under interview conditions with an interviewer |
| **L7** | Interview | Demonstrated in a mock interview round. | Two mock rounds with per-skill outcome ≥ 75 | Two SD mock rounds: caching 78 and 80 | 90–100 | counts | real interview outcome (no hiring guarantee) |

Mapping to the user-facing ladder:

| Statement | Level |
|---|---|
| "I studied this" | L0 |
| "I can recall this" | L1 |
| "I can solve this" (with help) | L2 |
| "I can solve this independently" | L3 |
| "I can solve this under time pressure" | L4 |
| "I can explain it" | L5 |
| "I can apply it to a real system / unfamiliar variant" | L6 |
| "I can handle an interview follow-up" | L5 (follow-up rubric) and L7 (in a mock) |

## 4. Outcome points (integer 0–100)

Problem attempts:

| Condition (first match wins) | Outcome points |
|---|---:|
| `outcome = FAIL` | 0 |
| `solution_viewed = true` | 20 |
| `outcome = PARTIAL` | 50 |
| `outcome = PASS` and `hints_used ≥ 2` | 60 |
| `outcome = PASS` and `hints_used = 1` | 80 |
| `outcome = PASS` and `hints_used = 0` | 100 |

Assessments, mock rounds and revision reviews: the recorded per-skill `outcome_points` (0–100), produced by the rubric of the mission template that generated them (`MISSION_LIBRARY.md`). For mock rounds with `source = SELF`, outcome points are capped at 80. Self-scored mocks cannot prove excellence.

Revision reviews have no points of their own: the linked observation's points apply (§5.6).

## 5. Level derivation (observation → evidence rows)

Exactly one evidence row exists per `(source_type, source_id, skill_id, ruleset_version)`. If several rules below target the same skill for the same observation, the row keeps the **minimum** outcome points and the level from the highest-precedence rule (rule order as listed).

### 5.1 Problem attempts: mapped skills

For every `problem_skills` mapping of the attempted problem, emit one row. The row level is computed top-down:

```text
prior     := earlier non-superseded attempts of this problem
is_unseen := prior is empty AND seen_elsewhere = false

# 1. ladder (always computed)
if solution_viewed or hints_used ≥ 1:
    level := L2
else:
    level := L3
    if timed and time_seconds ≤ time_limit_seconds and time_limit_seconds ≤ expected_minutes×60
       and difficulty ∈ {MEDIUM, HARD}:                   level := L4
    if level = L4 and explanation_score ≥ 7 and complexity_correct = true: level := L5
    if level = L5 and (difficulty = HARD or followup_solved = true):     level := L6
# 2. caps
if difficulty = EASY: level := min(level, L3)
if not is_unseen:                                          # memory, not problem-solving
    if prior is empty:            level := min(level, L3)  # seen_elsewhere only
    elif attempted_on − latest prior attempted_on ≥ 7 days: level := min(level, L3)
    else:                         level := min(level, L1)
```

A FAIL row keeps the level its conditions reached (e.g. an unhinted FAIL is an L3 row with 0 points). Failures therefore count against quality at the level they were attempted.

Row fields: `outcome_points` per §4, `difficulty_bp` from problem difficulty, `mapping_bp` = `problem_skills.mapping_weight_bp` (primary 10000, secondary 5000), `source_key = problem:<id>`.

### 5.2 Problem attempts: derived skill rows

| Raw field / condition | Skill | Outcome points | Level |
|---|---|---|---|
| `pattern_identified` not null and attempt `is_unseen` | `dsa.pattern_recognition` | 100 if true, 0 if false | L3; L4 if `timed`; L5 if `timed` and `explanation_score ≥ 7` |
| `complexity_correct` not null | `dsa.complexity_analysis` | 100 / 0 | attempt row level |
| `followup_solved` not null | `execution.followup_handling` | 100 / 0 | attempt row level |
| `execution_rubric.clarification` (0–10) | `execution.clarification` | value×10 | attempt row level |
| `execution_rubric.think_aloud` | `execution.think_aloud` | value×10 | attempt row level |
| `execution_rubric.testing` | `execution.testing_dry_run` | value×10 | attempt row level |
| `execution_rubric.time_management` | `execution.time_management` | value×10 | attempt row level |
| `execution_rubric.optimization` | `execution.brute_force_to_optimal` | value×10 | attempt row level |
| `outcome ∈ {PASS, PARTIAL}`, no hints, `pattern_identified ≠ false` | `execution.bug_free_coding` | 100 if PASS and no bug-class mistake; 50 if PASS with a bug-class mistake; 0 if PARTIAL | attempt row level |

`pattern_identified` means "named the correct approach **before** any hint or solution". The capture form asks it first.

### 5.3 Problem attempts: mistake routing (negative evidence)

Each `attempt_mistakes.mistake_code` emits a 0-point row on its routed skill at the attempt's row level (`mapping_bp` 10000):

| Mistake code | Routed skill(s) |
|---|---|
| `WRONG_PATTERN` | `dsa.pattern_recognition` |
| `NO_APPROACH` | — (the mapped-skill FAIL row is sufficient) |
| `MISREAD_PROBLEM` | `execution.clarification` |
| `EDGE_CASE_MISSED` | `execution.testing_dry_run` |
| `OFF_BY_ONE` | `execution.bug_free_coding` |
| `IMPLEMENTATION_BUG` | `execution.bug_free_coding` |
| `LANGUAGE_SYNTAX` | `python.core_syntax` |
| `DATA_STRUCTURE_API` | `python.collections` |
| `WRONG_COMPLEXITY` | `dsa.complexity_analysis`, `execution.brute_force_to_optimal` |
| `TIME_OVERRUN` | `execution.time_management` |

The bug-class mistakes are `OFF_BY_ONE`, `IMPLEMENTATION_BUG`, `LANGUAGE_SYNTAX`, `DATA_STRUCTURE_API`.

### 5.4 Assessments

Each assessment has `kind`, conditions, and one or more `assessment_skills(skill_id, outcome_points, mapping_weight_bp)` rows. One evidence row is emitted per assessment skill.

| Kind | Level rule |
|---|---|
| `STUDY_SESSION` | L0, non-scoring (records minutes only) |
| `SELF_ASSESSMENT` | L0, non-scoring; `familiarity ∈ {NONE, SOME, SOLID}` (§5.7) |
| `RECALL_QUIZ` | L1 if closed-book; L0 non-scoring if `notes_used` |
| `PATTERN_DRILL` | on `dsa.pattern_recognition`: L3; L4 if `timed` and within limit; L5 if additionally `followup_points ≥ 70` (justified each choice). Points = correct × 20 (5 statements). On each pattern skill in the drill: L1, points = its statements correct / its statements × 100 |
| `CONCEPT_EXPLAIN`, `CODE_EXERCISE`, `ESTIMATION_DRILL`, `SD_DESIGN`, `LLD_DESIGN`, `MACHINE_CODING`, `STORY_REHEARSAL`, `PROJECT_WALKTHROUGH` | practice ladder below |
| `APPLIED_TASK` | L6 if `outcome_points ≥ 70` and `followup_points ≥ 70`; otherwise L3 |

Practice ladder (top-down):

```text
level := L2 if notes_used or hints_used > 0 or reference_used else L3
if level = L3 and timed and time_seconds ≤ time_limit_seconds:         level := L4
if level = L4 and followup_points ≥ 70:                                level := L5
if level = L5 and (peer_evaluated or unseen_variant):                  level := L6
```

`time_limit_seconds` must not exceed the template's limit (`MISSION_LIBRARY.md`). A longer limit is recorded but treated as untimed.

`source_key` = `prompt:<prompt_key>` (concepts, quizzes), `exercise:<exercise_key>` (design/LLD/machine coding), `story:<story_id>`, `project:<project_key>`. Repeating the same prompt does not add diversity. Learning content records `content:<content_key>` (`#<milestone>` / `#defense` for projects); the learning layer only fills in the fields above and never changes a level rule (LEARNING_ENGINE.md §3, D-083).

### 5.5 Mock rounds

Each `mock_round_skills(skill_id, outcome_points, is_weakness)` row emits L7 evidence with `source_key = mock_round:<id>`. Outcome is capped at 80 if `mock.source = SELF`. Rows with `is_weakness = true` also feed `MOCK_WEAKNESS` (gap engine) and create revision items (revision engine).

### 5.6 Revision reviews

A revision review always links to the observation that performed it (an attempt with `mode = REVISION` or an assessment). The evidence comes from that observation under §5.1–5.4. Re-solved problems are not unseen, so they cap at L3 (≥ 7 days since exposure) or L1. Concept explanations are not capped: explaining a concept again without notes *is* the skill.

### 5.7 Self-assessment and declared unknown

- `familiarity = NONE` (**declared unknown**): if the skill has no scoring rows, the skill becomes assessed with `score = 0`, `level = L0`, `confidence = LOW`. It is ignored once any scoring row exists.
- `familiarity ∈ {SOME, SOLID}`: no state effect. It only routes the mentor (DIAGNOSE vs LEARN) and is stored as a self-rating.
- `self_rating_before` / `self_rating_after` on any observation: stored, used only by the CONFIDENCE gap type (`GAP_ENGINE.md` §6).

## 6. Weights

Each evidence row's weight is an exact integer product:

```text
weight = recency_bp × difficulty_bp × mapping_bp
```

| Recency (as_of_date − observed_on) | `recency_bp` |
|---|---:|
| 0–30 days | 10000 |
| 31–60 | 8500 |
| 61–90 | 7000 |
| 91–120 | 5500 |
| > 120 | 3000 |

| Difficulty | `difficulty_bp` | Level cap |
|---|---:|---|
| EASY | 8000 | L3 |
| MEDIUM (default for assessments) | 10000 | — |
| HARD | 12000 | — |

`mapping_bp`: primary skill 10000, secondary skill 5000. Derived, routed, assessment (default) and mock rows use 10000. Mock rows use `difficulty_bp` 10000.

## 7. Skill state calculation

A **scoring row** is an evidence row with level ≥ L1. Study and self-assessment rows are never scoring rows.

### 7.1 Level qualification (repeated success + diversity)

A row *qualifies for level L* if `row.level ≥ L` **and** `row.outcome_points ≥ QUAL_MIN[L]` **and** its age is ≤ 120 days. The one exception is L1, which old rows can also qualify for.

| Level | Rows needed | Distinct source keys | `QUAL_MIN` (points) | Age window |
|---|---:|---:|---:|---|
| L1 | 1 | 1 | 60 | any age |
| L2 | 2 | 2 | 60 | ≤ 120 days |
| L3 | 2 | 2 | 70 | ≤ 120 days |
| L4 | 2 | 2 | 70 | ≤ 120 days |
| L5 | 2 | 2 | 70 | ≤ 120 days |
| L6 | 2 | 2 | 70 | ≤ 120 days |
| L7 | 2 | 2 (distinct mock rounds) | 75 | ≤ 120 days |

`level` = the highest L whose requirement is met, or L0 if none is met. "Repeated success" is exactly this rule: one success is never enough above L1, and repeating the same source key does not count twice.

### 7.2 Quality

```text
considered := scoring rows with row.level ≥ max(level − 1, 1)               (all ages, recency-weighted)
            ∪ scoring rows with outcome_points < 60 and age ≤ 120 days       (recent failures at ANY level)
quality    := Σ(outcome_points × weight) / Σ(weight)                         (Decimal, 0–100)
```

Failures always pull quality down, including failures on easier tasks: a timed-level skill that fails an untimed problem is not as strong as its level suggests. Successes far below the current level are ignored, so easy wins cannot inflate a high level.

### 7.3 Score

```text
BAND = {L0: (0,10), L1: (10,30), L2: (30,45), L3: (45,60), L4: (60,72), L5: (72,82), L6: (82,90), L7: (90,100)}
score := round_half_up( lo + (hi − lo) × quality / 100 )
```

- **Interview reality cap:** if the skill's most recent L7 row is ≤ 60 days old and has `outcome_points < 70`, then `score := min(score, that outcome_points)`. Practice evidence cannot outweigh a recent failed interview round. The cap lifts when a newer L7 row reaches ≥ 70, or the failing row passes 60 days of age. `level` is not changed (the gap engine uses the practice level to diagnose INTERVIEW_EXECUTION).
- **Unassessed** (no scoring rows, no declared unknown): `score = null`, `level = null`, `confidence = NONE`.
- **Declared unknown only:** `score = 0`, `level = L0`, `confidence = LOW`.

### 7.4 Peak score

`peak_score` uses the same algorithm with every row's `recency_bp = 10000`, no age window for any level, and no interview reality cap. It is the best the skill has ever demonstrated. It is used for RETENTION detection.

## 8. Confidence

Computed over scoring rows of age ≤ 120 days, except NONE:

| Confidence | Rule (first match from the top) |
|---|---|
| `NONE` | no scoring rows of any age and no declared unknown |
| `HIGH` | count ≥ 6 **and** distinct source keys ≥ 3 **and** at least one row ≤ 30 days old **and** rows span ≥ 2 distinct levels |
| `MEDIUM` | count ≥ 3 **and** distinct source keys ≥ 2 |
| `LOW` | otherwise |

Confidence is never derived from self-rating and never raises the score.

## 9. Effective score

```text
UNCERTAINTY = {LOW: 15, MEDIUM: 7, HIGH: 0}
effective_score := max(score − UNCERTAINTY[confidence], 0)        (null when unassessed)
```

Every downstream consumer uses `effective_score`: gaps, floors, components, gates. `score` is used only for prerequisite satisfaction and display.

## 10. Skill labels (display only, on `effective_score`)

| Label | Range |
|---|---|
| `UNASSESSED` | null |
| `WEAK` | 0–44 |
| `DEVELOPING` | 45–59 |
| `WORKING` | 60–71 |
| `STRONG` | 72–81 |
| `INTERVIEW_GRADE` | 82–100 |

## 11. Arithmetic rules

- Stored scores, points, levels and minutes are integers. Weights are integers (basis points; a product of three bp values fits easily in 64-bit).
- Intermediate ratios use `decimal.Decimal` with the default context (precision 28). Never `float`.
- Rounding happens **once**, at the final value, with `ROUND_HALF_UP` to an integer.
- Dates are local `DATE`s in the user's timezone. Age in days = `(as_of_date − observed_on).days`.

## 12. Worked examples

All examples use as_of `2026-11-02`, MEDIUM difficulty, primary mapping.

**E1. Two clean unseen solves (untimed).**
- Rows: two L3 rows, 100 points each, distinct problems, ages 3 and 10 days.
- Qualifies L3 (two distinct rows ≥ 70). L4 needs timed rows, so level = L3.
- Quality: both rows are considered → 100. Score = 45 + 15 × 100/100 = **60**.
- Confidence: count 2, so LOW. Effective = 60 − 15 = **45** (DEVELOPING).

**E2. Graph skill with pattern failures.**
- Rows: 5 unseen, unhinted attempts on 5 problems in the last 14 days: 2 PASS (L3, 100) and 3 FAIL (L3, 0, `pattern_identified = false`).
- Level L3. Quality = (2×100 + 3×0)/5 = 40. Score = 45 + 15 × 0.40 = **51**.
- Confidence: count 5, distinct 5, recent, but only one distinct level (L3), so MEDIUM. Effective = 51 − 7 = **44** (WEAK).
- `dsa.pattern_recognition` also receives the 2×100 + 3×0 rows.

**E3. Timed but weak explanation.**
- Rows: 3 unseen timed PASSes within limit, explanation 6/10, so each row is L4 (L5 needs ≥ 7).
- Level L4. Quality 100. Score = 60 + 12 × 1 = **72**.
- Confidence: count 3, distinct 3, so MEDIUM. Effective = **65** (WORKING).

**E4. Self-rating has no effect.** E1 plus `self_rating_before = 5` on both rows: score 60, confidence LOW. Identical to E1.

**E5. Decay.**
- Rows: an L4 skill with 2 qualifying rows, both now 130 days old (quality 100).
- Those rows can no longer qualify L2–L7. They still qualify L1 (any age, ≥ 60).
- Level L1. Quality: considered rows are level ≥ 1, i.e. both rows, at recency 3000 → 100. Score = 10 + 20 × 1 = **30**.
- Confidence: no rows ≤ 120 days → LOW. Effective **15**.
- Peak score (no window): **72**. Peak − score = 42, so the RETENTION gap type fires.

## 13. Constants (ruleset `v1`)

| Constant | Value |
|---|---|
| `OUTCOME_POINTS` | §4 table |
| `RECENCY_BP` | 0–30: 10000; 31–60: 8500; 61–90: 7000; 91–120: 5500; > 120: 3000 |
| `DIFFICULTY_BP` | EASY 8000, MEDIUM 10000, HARD 12000 |
| `MAPPING_BP` | primary 10000, secondary 5000 |
| `EASY_LEVEL_CAP` | L3 |
| `SEEN_PROBLEM_CAP` | L3 if ≥ 7 days since exposure, else L1 |
| `LEVEL_WINDOW_DAYS` | 120 (L1: unlimited) |
| `QUAL` | §7.1 table |
| `BANDS` | §7.3 |
| `L5_MIN_EXPLANATION` | 7 (of 10) |
| `FOLLOWUP_MIN_POINTS` | 70 |
| `SELF_MOCK_OUTCOME_CAP` | 80 |
| `INTERVIEW_REALITY_CAP` | most recent L7 row ≤ 60 days old with < 70 points caps the score at its points |
| `CONFIDENCE` | §8 |
| `UNCERTAINTY` | LOW 15, MEDIUM 7, HIGH 0 |
| `DEFAULT_EXPECTED_MINUTES` | EASY 15, MEDIUM 30, HARD 45 (when a problem has none) |
