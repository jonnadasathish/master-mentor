# Master Mentor — Mission Library (Spec v2, `seed-v1`)

**Machine-readable source:** [`seed/mission_templates.yaml`](../../seed/mission_templates.yaml). The tables in §5 are generated from it; if they disagree, the YAML wins.

A **mission template** turns a gap's recommended focus into concrete work: how long, how hard, what must be recorded, and what counts as passing. The mentor (`MENTOR_ENGINE.md` §7) selects templates. The evidence model (`EVIDENCE_MODEL.md` §5) turns what you record into evidence.

## 1. Template identity and lookup

Templates are keyed by **component + stage**, optionally narrowed by **gap type** and/or **applies_to** (skill keys or key prefixes ending in `.`).

Lookup, most specific first; ties go to the lowest `key`:

1. component + stage + gap type + applies_to
2. component + stage + applies_to
3. component + stage + gap type
4. component + stage
5. `generic` + stage

**Seed validator rule:** every `(component, stage)` pair reachable from the gap engine resolves to a template. This is verified for `seed-v1` (86 templates) by `make seed-validate` (code `templates.coverage`). Durations are a positive `minutes`, or a `minutes_rule` (revision/mock templates only); observation kinds come from a closed list, with `ITEM_DEFINED` meaning "decided by the revision item". If a candidate still finds no template, it is dropped with `CONTENT_MISSING`.

## 2. Stages and the evidence level they target

| Stage | Purpose | Targets level | Typical gap types |
|---|---|---|---|
| `DIAGNOSE` | Measure an unassessed skill | whatever is shown | UNASSESSED |
| `LEARN` | First exposure + closed-book check | L1 (L2) | KNOWLEDGE (L0), LEVEL_UP at L0 |
| `RECALL` | Closed-book retrieval | L1 | KNOWLEDGE, CONFIDENCE (≤ L1) |
| `GUIDED` | Solve with a hint ladder / notes | L2 → L3 | PRACTICE (L1), leech override |
| `INDEPENDENT` | Solve alone, untimed | L3 | PRACTICE (L2), CONFIDENCE |
| `TIMED` | Solve within the interview limit | L4 | SPEED, LEVEL_UP (L3) |
| `EXPLAIN` | Timed + explanation / follow-ups | L5 | DEPTH, LEVEL_UP (L4) |
| `TRANSFER` | Harder / unseen variant / applied / peer | L6 | EXPERIENCE, LEVEL_UP (L5) |
| `SIMULATE` | Interview-condition rehearsal | L5–L6 (L7 only in real mock rounds) | INTERVIEW_EXECUTION, LEVEL_UP (L6+) |
| `PATTERN_DRILL` | Classify statements by pattern | L3–L4 on `dsa.pattern_recognition` | PATTERN_RECOGNITION |
| `THINK_ALOUD` | Recorded delivery, communication rubric | L3–L4 | COMMUNICATION |
| `REINFORCE` | Re-study, then closed-book retry | L3 | RETENTION, revision with `needs_reinforcement` |
| `REVISION` | Scheduled revision item review | per item type | (revision engine, not gap types) |

## 3. Common rules for every mission

- **Difficulty:** the mentor's problem-picker table (`MENTOR_ENGINE.md` §7) is authoritative; a template's `difficulty` is documentation and fallback.
- **Required evidence:** a mission is DONE only with its observation recorded (`plan_items.observation_*`). Otherwise it is marked `no_evidence`, which records a non-scoring `STUDY_SESSION`.
- **Time limits:** `limit = expected` means the problem's `expected_minutes`. A template's `limit_seconds` is the maximum allowed for L4 credit (`EVIDENCE_MODEL.md` §5.4).
- **Self-graded rubrics:**
  - Assessments are graded against an answer key or rubric card (§4) **before** looking at notes.
  - Grades are 0–100 per skill. Self-grading is accepted because it is checked against a key.
  - `peer_evaluated` and mocks provide the independent check.
- **`next_on_pass` / `next_on_fail`:**
  - These are *advisory* stage hints shown to the user.
  - The authoritative next stage is always re-derived by the gap engine from the new evidence (`GAP_ENGINE`).
  - `MOCK` means "ready for a mock round".
- **Minimum budget:** templates with `min_budget` are scheduled only on days whose budget is at least that (machine coding 90, final simulation 160).

## 4. Rubric cards (used by self-graded templates)

| Card | Dimensions (each 0–10 → ×10 points or summed to 100) |
|---|---|
| DSA explanation (`explanation_score`) | approach, invariant, complexity, trade-off vs alternative, edge cases (2 each = 10) |
| Execution rubric (`execution_rubric`) | clarification, think_aloud, testing, time_management, optimization (0–10 each) |
| CS answer | correct core (40), mechanism/why (30), example (15), trade-off/failure mode (15) |
| SD design (per framework step → skill) | requirements → `sd.requirements_scoping`; estimation → `sd.capacity_estimation`; API → `sd.api_design`; data model → `sd.data_modeling`; HLD → `sd.high_level_decomposition`; deep dive → `sd.deep_dive_bottlenecks` and the building-block skills used; trade-offs → `sd.tradeoff_articulation`; time → `sd.time_boxing` |
| LLD design | entities/use cases → `lld.requirements_entities`; classes/interfaces → `lld.class_design`; patterns → `lld.design_patterns`; change handling → `lld.extensibility`; thread safety → `lld.concurrency_safety` |
| Machine coding | runs end-to-end (30), modular structure (25), extensibility (15), tests (20), naming/readability (10) |
| Story (STAR) | direct answer (15), situation/task brevity (15), own actions (30), measurable result (25), lesson (15); `communication_points` = structure + pacing + directness |
| Project walkthrough | context (10), architecture clarity (25), decisions + alternatives (25), numbers (20), failure/incident (20) |

## 4a. Coverage

All required mission categories are present:

| Category | Templates |
|---|---|
| DSA | `dsa.*` (11) |
| CS | `cs.*` (12, including DBMS labs `cs.dbms_query_lab`, `cs.dbms_transaction_lab` and `cs.concurrency_lab`) |
| System design | `system_design.*` (10, including the sub-step `system_design.drill`) |
| LLD | `lld.*` (9, including `lld.machine_coding`) |
| Behavioral | `behavioral.*` (9) |
| Interview execution | `coding.execution_drill`, `coding.think_aloud`, `coding.simulate` |
| Revision | `revision.*` (9) |
| Mock preparation | `mock.prep`, `mock.round`, `mock.final_simulation` |

## 5. Templates

### DSA (`dsa`)

| Key | Stage | Applies to / gap | Min | Difficulty | Observation (required evidence) | Pass criteria | Output level | Next on pass / fail |
|---|---|---|---:|---|---|---|---|---|
| `dsa.diagnose` | DIAGNOSE | any | 40 | MEDIUM | `ATTEMPT` — timed; limit = expected min; records pattern_identified, self_rating_before, mistakes | outcome == PASS and hints_used == 0 | L4 | GAP_ENGINE / GAP_ENGINE |
| `dsa.learn` | LEARN | any | 45 | EASY | `STUDY_SESSION + RECALL_QUIZ + ATTEMPT` — 25 min study of pattern + invariant; 5-question closed-book quiz; 1 easy problem with hints allowed | recall_quiz.outcome_points >= 60 | L2 | GUIDED / LEARN |
| `dsa.recall` | RECALL | any | 15 | — | `RECALL_QUIZ` — write the pattern template + invariant + 2 trigger signals from memory, check against notes | outcome_points >= 60 | L1 | GUIDED / LEARN |
| `dsa.guided` | GUIDED | any | 30 | EASY | `ATTEMPT` | outcome == PASS and hints_used <= 1 and not solution_viewed | L3 | INDEPENDENT / GUIDED |
| `dsa.independent` | INDEPENDENT | any | 35 | MEDIUM | `ATTEMPT` — records pattern_identified | outcome == PASS and hints_used == 0 | L3 | TIMED / GUIDED |
| `dsa.timed` | TIMED | any | 40 | MEDIUM | `ATTEMPT` — timed; limit = expected min; records pattern_identified | outcome == PASS and hints_used == 0 and time_seconds <= time_limit_seconds | L4 | EXPLAIN / INDEPENDENT |
| `dsa.explain` | EXPLAIN | any | 40 | MEDIUM | `ATTEMPT` — timed; limit = expected min; records explanation_score, complexity_correct | L4 conditions and explanation_score >= 7 and complexity_correct | L5 | TRANSFER / TIMED |
| `dsa.transfer` | TRANSFER | any | 50 | HARD | `ATTEMPT` — timed; limit = expected min; records explanation_score, complexity_correct, followup_solved | L5 conditions and (difficulty == HARD or followup_solved) | L6 | SIMULATE / EXPLAIN |
| `dsa.simulate` | SIMULATE | any | 45 | MEDIUM | `ATTEMPT` — timed; recorded_audio; limit = expected min; records execution_rubric, explanation_score, complexity_correct, followup_solved | outcome == PASS and execution_rubric mean >= 7 | L6 | MOCK / EXPLAIN |
| `dsa.pattern_drill` | PATTERN_DRILL | any | 25 | — | `PATTERN_DRILL` — timed; limit 8 min; classify 5 statements (name pattern + key invariant), then sketch approach for the 2 target-pattern statements; statements stay unseen-for-solving | correct >= 4 of 5 (partial: correct == 3) | L4 | INDEPENDENT / PATTERN_DRILL |
| `dsa.reinforce` | REINFORCE | any | 30 | — | `STUDY_SESSION + ATTEMPT` — 10 min re-read own canonical notes, then re-solve the canonical problem cold | outcome == PASS and hints_used == 0 | L3 | GAP_ENGINE / GUIDED |

### Coding & interview execution (`coding`)

| Key | Stage | Applies to / gap | Min | Difficulty | Observation (required evidence) | Pass criteria | Output level | Next on pass / fail |
|---|---|---|---:|---|---|---|---|---|
| `coding.diagnose` | DIAGNOSE | any | 30 | EASY | `CODE_EXERCISE` — timed; limit 25 min; 5 Python warm-ups covering the unassessed python.* skills; per-skill outcome | outcome_points >= 70 per skill | L4 | GAP_ENGINE / GAP_ENGINE |
| `coding.learn` | LEARN | any | 40 | EASY | `STUDY_SESSION + CODE_EXERCISE` — study the idiom/API, then 3 exercises with docs open | outcome_points >= 60 | L2 | GUIDED / LEARN |
| `coding.guided` | GUIDED | any | 25 | EASY | `CODE_EXERCISE` — reference_used | outcome_points >= 70 | L2 | INDEPENDENT / LEARN |
| `coding.independent` | INDEPENDENT | any | 25 | MEDIUM | `CODE_EXERCISE` | outcome_points >= 70 | L3 | TIMED / GUIDED |
| `coding.timed` | TIMED | any | 25 | MEDIUM | `CODE_EXERCISE` — timed; limit 20 min | outcome_points >= 70 within limit | L4 | EXPLAIN / INDEPENDENT |
| `coding.explain` | EXPLAIN | any | 25 | MEDIUM | `CODE_EXERCISE` — timed; limit 20 min; records followup_points; solve, then explain complexity of each built-in used and one alternative | followup_points >= 70 | L5 | TRANSFER / TIMED |
| `coding.transfer` | TRANSFER | any | 45 | — | `APPLIED_TASK` — records followup_points; use the idiom in real code (own project or a small tool) and defend the choice | outcome_points >= 70 and followup_points >= 70 | L6 | SIMULATE / EXPLAIN |
| `coding.execution_drill` | GUIDED, INDEPENDENT, TIMED, EXPLAIN | `execution.*` | 40 | MEDIUM | `ATTEMPT` — timed; limit = expected min; records execution_rubric, mistakes, followup_solved; solve a DSA problem focusing on the target execution skill; self-score the 5-dimension rubric (0-10) against the rubric card | target rubric dimension >= 7 and outcome == PASS | L4 | GAP_ENGINE / GUIDED |
| `coding.think_aloud` | THINK_ALOUD | any | 40 | MEDIUM | `ATTEMPT` — timed; recorded_audio; limit = expected min; records execution_rubric | execution_rubric.think_aloud >= 7 and execution_rubric.clarification >= 7 | L4 | GAP_ENGINE / THINK_ALOUD |
| `coding.simulate` | SIMULATE | any | 45 | MEDIUM | `ATTEMPT` — timed; recorded_audio; limit = expected min; records execution_rubric, followup_solved | outcome == PASS and execution_rubric mean >= 7 | L4 | MOCK / THINK_ALOUD |

### CS fundamentals (incl. DBMS) (`cs`)

| Key | Stage | Applies to / gap | Min | Difficulty | Observation (required evidence) | Pass criteria | Output level | Next on pass / fail |
|---|---|---|---:|---|---|---|---|---|
| `cs.diagnose` | DIAGNOSE | any | 20 | — | `RECALL_QUIZ` — 10 closed-book questions covering up to 3 unassessed skills of one group; per-skill outcome | outcome_points >= 60 per skill | L1 | GAP_ENGINE / GAP_ENGINE |
| `cs.learn` | LEARN | any | 40 | — | `STUDY_SESSION + RECALL_QUIZ` — 25 min study, one-page notes in own words, 5-question closed-book quiz | recall_quiz.outcome_points >= 60 | L1 | GUIDED / LEARN |
| `cs.recall` | RECALL | any | 15 | — | `RECALL_QUIZ` | outcome_points >= 60 | L1 | GUIDED / LEARN |
| `cs.guided` | GUIDED | any | 20 | — | `CONCEPT_EXPLAIN` — notes_used | outcome_points >= 70 | L2 | INDEPENDENT / RECALL |
| `cs.independent` | INDEPENDENT | any | 20 | — | `CONCEPT_EXPLAIN` | outcome_points >= 70 | L3 | TIMED / GUIDED |
| `cs.timed` | TIMED | any | 20 | — | `CONCEPT_EXPLAIN` — timed; limit 15 min; rapid-fire interview questions | outcome_points >= 70 within limit | L4 | EXPLAIN / INDEPENDENT |
| `cs.explain` | EXPLAIN | any | 25 | — | `CONCEPT_EXPLAIN` — timed; limit 15 min; records followup_points; why/trade-off/failure-mode questions | followup_points >= 70 | L5 | TRANSFER / TIMED |
| `cs.transfer` | TRANSFER | any | 60 | — | `APPLIED_TASK` — records followup_points | outcome_points >= 70 and followup_points >= 70 | L6 | SIMULATE / EXPLAIN |
| `cs.simulate` | SIMULATE | any | 30 | — | `CONCEPT_EXPLAIN` — timed; recorded_audio; limit 30 min; records followup_points, communication_points | outcome_points >= 70 | L5 | MOCK / EXPLAIN |
| `cs.dbms_query_lab` | INDEPENDENT, TIMED | `db.sql_querying`, `db.indexing`, `db.query_optimization`, `db.modeling_normalization` | 35 | MEDIUM | `CODE_EXERCISE` — write queries against the seeded practice schema in local MySQL; run EXPLAIN; justify index choice | outcome_points >= 70 | L4 | EXPLAIN / GUIDED |
| `cs.dbms_transaction_lab` | TRANSFER | `db.transactions_acid`, `db.isolation_mvcc`, `db.locking_deadlocks` | 60 | — | `APPLIED_TASK` — records followup_points; two MySQL sessions: reproduce an anomaly or deadlock, explain why, fix it | outcome_points >= 70 and followup_points >= 70 | L6 | SIMULATE / EXPLAIN |
| `cs.concurrency_lab` | TRANSFER | `os.synchronization`, `os.concurrency_practical`, `os.deadlocks` | 60 | — | `APPLIED_TASK` — records followup_points; implement a bounded blocking queue or thread pool in Python with tests; explain the race it prevents | outcome_points >= 70 and followup_points >= 70 | L6 | SIMULATE / EXPLAIN |

### LLD / OOD / machine coding (`lld`)

| Key | Stage | Applies to / gap | Min | Difficulty | Observation (required evidence) | Pass criteria | Output level | Next on pass / fail |
|---|---|---|---:|---|---|---|---|---|
| `lld.diagnose` | DIAGNOSE | any | 45 | — | `LLD_DESIGN` — untimed small design (e.g. parking lot lite); rubric per lld.* skill | outcome_points >= 70 per skill | L3 | GAP_ENGINE / GAP_ENGINE |
| `lld.learn` | LEARN | any | 45 | — | `STUDY_SESSION + RECALL_QUIZ + CODE_EXERCISE` — study principle/pattern, quiz, small refactor exercise | recall_quiz.outcome_points >= 60 | L2 | GUIDED / LEARN |
| `lld.guided` | GUIDED | any | 45 | — | `LLD_DESIGN` — reference_used | outcome_points >= 70 | L2 | INDEPENDENT / LEARN |
| `lld.independent` | INDEPENDENT | any | 60 | — | `LLD_DESIGN` — requirements -> entities -> class diagram -> key method signatures -> 1 sequence | outcome_points >= 70 | L3 | TIMED / GUIDED |
| `lld.timed` | TIMED | any | 60 | — | `LLD_DESIGN` — timed; limit 45 min | outcome_points >= 70 within limit | L4 | EXPLAIN / INDEPENDENT |
| `lld.explain` | EXPLAIN | any | 40 | — | `LLD_DESIGN` — timed; limit 40 min; records followup_points; 3 change requests against own design; show what changes | followup_points >= 70 | L5 | TRANSFER / TIMED |
| `lld.machine_coding` | INDEPENDENT, TIMED, EXPLAIN, TRANSFER | `lld.machine_coding` | 90 | — | `MACHINE_CODING` — timed; limit 90 min; records followup_points; working, modular, tested Python in 90 min; rubric: runs, structure, extensibility, tests, naming | outcome_points >= 70 within limit | L5 | TRANSFER / INDEPENDENT |
| `lld.transfer` | TRANSFER | any | 60 | — | `LLD_DESIGN` — unseen_variant; records followup_points; unseen variant or peer review | L5 conditions and (peer_evaluated or unseen_variant) | L6 | SIMULATE / EXPLAIN |
| `lld.simulate` | SIMULATE | any | 60 | — | `LLD_DESIGN` — timed; recorded_audio; limit 60 min; records followup_points, communication_points | outcome_points >= 70 | L5 | MOCK / EXPLAIN |

### System design (`system_design`)

| Key | Stage | Applies to / gap | Min | Difficulty | Observation (required evidence) | Pass criteria | Output level | Next on pass / fail |
|---|---|---|---:|---|---|---|---|---|
| `system_design.diagnose` | DIAGNOSE | any | 45 | — | `SD_DESIGN` — untimed URL-shortener-class design; rubric row per framework step -> sd.* skill | outcome_points >= 70 per skill | L3 | GAP_ENGINE / GAP_ENGINE |
| `system_design.learn` | LEARN | any | 40 | — | `STUDY_SESSION + RECALL_QUIZ` — study building block, 5-question quiz, one-paragraph application to a known system | recall_quiz.outcome_points >= 60 | L1 | GUIDED / LEARN |
| `system_design.recall` | RECALL | any | 15 | — | `RECALL_QUIZ` | outcome_points >= 60 | L1 | GUIDED / LEARN |
| `system_design.guided` | GUIDED | any | 45 | — | `SD_DESIGN` — reference_used | outcome_points >= 70 | L2 | INDEPENDENT / RECALL |
| `system_design.independent` | INDEPENDENT | any | 60 | — | `SD_DESIGN` — full design without notes, untimed, 10-step framework | outcome_points >= 70 | L3 | TIMED / GUIDED |
| `system_design.timed` | TIMED | any | 50 | — | `SD_DESIGN` — timed; limit 45 min | outcome_points >= 70 within limit | L4 | EXPLAIN / INDEPENDENT |
| `system_design.explain` | EXPLAIN | any | 30 | — | `SD_DESIGN` — timed; limit 25 min; records followup_points; defend own design against 3 probes: failure, scale x10, consistency | followup_points >= 70 | L5 | TRANSFER / TIMED |
| `system_design.drill` | GUIDED, INDEPENDENT, TIMED, EXPLAIN | `sd.capacity_estimation`, `sd.requirements_scoping`, `sd.api_design`, `sd.data_modeling`, `sd.deep_dive_bottlenecks`, `sd.tradeoff_articulation`, `sd.time_boxing` | 20 | — | `ESTIMATION_DRILL + SD_DESIGN` — timed; limit 15 min; one sub-step on 2 fresh prompts (e.g. estimate QPS/storage/bandwidth) | outcome_points >= 70 | L4 | GAP_ENGINE / GUIDED |
| `system_design.transfer` | TRANSFER | any | 60 | — | `SD_DESIGN + APPLIED_TASK` — records followup_points; peer-reviewed design or apply to own/real system | L5 conditions and (peer_evaluated or applied) | L6 | SIMULATE / EXPLAIN |
| `system_design.simulate` | SIMULATE | any | 50 | — | `SD_DESIGN` — timed; recorded_audio; limit 45 min; records followup_points, communication_points | outcome_points >= 70 | L5 | MOCK / EXPLAIN |

### Behavioral (`behavioral`)

| Key | Stage | Applies to / gap | Min | Difficulty | Observation (required evidence) | Pass criteria | Output level | Next on pass / fail |
|---|---|---|---:|---|---|---|---|---|
| `behavioral.diagnose` | DIAGNOSE | any | 20 | — | `STORY_REHEARSAL` — answer 2 competency questions cold, recorded; rubric | outcome_points >= 70 per skill | L3 | GAP_ENGINE / GAP_ENGINE |
| `behavioral.learn` | LEARN | any | 30 | — | `STUDY_SESSION + STORY_REHEARSAL` — notes_used; draft STAR story with a metric and a lesson; rehearse once with notes | outcome_points >= 60 | L2 | INDEPENDENT / LEARN |
| `behavioral.guided` | GUIDED | any | 15 | — | `STORY_REHEARSAL` — notes_used | outcome_points >= 70 | L2 | INDEPENDENT / LEARN |
| `behavioral.independent` | INDEPENDENT | any | 15 | — | `STORY_REHEARSAL` | outcome_points >= 70 | L3 | TIMED / GUIDED |
| `behavioral.timed` | TIMED | any | 15 | — | `STORY_REHEARSAL` — timed; recorded_audio; limit 3 min | outcome_points >= 70 within limit | L4 | EXPLAIN / INDEPENDENT |
| `behavioral.explain` | EXPLAIN | any | 20 | — | `STORY_REHEARSAL` — timed; limit 3 min; records followup_points; 3 probing follow-ups: what would you do differently, numbers, your exact role | followup_points >= 70 | L5 | TRANSFER / TIMED |
| `behavioral.structure_drill` | THINK_ALOUD | any | 20 | — | `STORY_REHEARSAL` — timed; recorded_audio; limit 3 min; records communication_points; re-deliver 2 stories: direct answer first, STAR, one metric, under 3 minutes | communication_points >= 70 | L4 | GAP_ENGINE / THINK_ALOUD |
| `behavioral.transfer` | TRANSFER | any | 30 | — | `STORY_REHEARSAL` — peer_evaluated; records followup_points | L5 conditions and peer_evaluated | L6 | SIMULATE / EXPLAIN |
| `behavioral.simulate` | SIMULATE | any | 30 | — | `STORY_REHEARSAL` — timed; recorded_audio; limit 30 min; records followup_points, communication_points; 4 questions back-to-back | outcome_points >= 70 | L5 | MOCK / EXPLAIN |

### Project deep dive & engineering (`project`)

| Key | Stage | Applies to / gap | Min | Difficulty | Observation (required evidence) | Pass criteria | Output level | Next on pass / fail |
|---|---|---|---:|---|---|---|---|---|
| `project.diagnose` | DIAGNOSE | any | 25 | — | `PROJECT_WALKTHROUGH` — walk through own main project cold, recorded | outcome_points >= 70 per skill | L3 | GAP_ENGINE / GAP_ENGINE |
| `project.learn` | LEARN | any | 40 | — | `STUDY_SESSION + PROJECT_WALKTHROUGH` — notes_used; write architecture brief: diagram, 3 decisions + alternatives, numbers, one incident | outcome_points >= 60 | L2 | INDEPENDENT / LEARN |
| `project.guided` | GUIDED | any | 20 | — | `PROJECT_WALKTHROUGH` — notes_used | outcome_points >= 70 | L2 | INDEPENDENT / LEARN |
| `project.independent` | INDEPENDENT | any | 20 | — | `PROJECT_WALKTHROUGH` | outcome_points >= 70 | L3 | TIMED / GUIDED |
| `project.timed` | TIMED | any | 15 | — | `PROJECT_WALKTHROUGH` — timed; recorded_audio; limit 10 min | outcome_points >= 70 within limit | L4 | EXPLAIN / INDEPENDENT |
| `project.explain` | EXPLAIN | any | 25 | — | `PROJECT_WALKTHROUGH` — timed; limit 10 min; records followup_points; 5 why-questions on own decisions; what breaks at 10x | followup_points >= 70 | L5 | TRANSFER / TIMED |
| `project.transfer` | TRANSFER | any | 30 | — | `PROJECT_WALKTHROUGH` — peer_evaluated; records followup_points | L5 conditions and peer_evaluated | L6 | SIMULATE / EXPLAIN |
| `project.engineering_lab` | INDEPENDENT, TIMED, TRANSFER | `engineering.*`, `testing.*` | 60 | — | `APPLIED_TASK` — records followup_points; real change in own codebase (e.g. add tests, profile and fix a slow query); write what/why | outcome_points >= 70 | L6 | GAP_ENGINE / INDEPENDENT |
| `project.simulate` | SIMULATE | any | 30 | — | `PROJECT_WALKTHROUGH` — timed; recorded_audio; limit 30 min; records followup_points, communication_points | outcome_points >= 70 | L5 | MOCK / EXPLAIN |

### Generic fallbacks (`generic`)

| Key | Stage | Applies to / gap | Min | Difficulty | Observation (required evidence) | Pass criteria | Output level | Next on pass / fail |
|---|---|---|---:|---|---|---|---|---|
| `generic.recall` | RECALL | any | 15 | — | `RECALL_QUIZ` | outcome_points >= 60 | L1 | GUIDED / LEARN |
| `generic.reinforce` | REINFORCE | any | 25 | — | `STUDY_SESSION + CONCEPT_EXPLAIN` — 10 min re-study own notes, then closed-book explanation/exercise | outcome_points >= 70 | L3 | GAP_ENGINE / GUIDED |
| `generic.think_aloud` | THINK_ALOUD | any | 30 | — | `CONCEPT_EXPLAIN` — recorded_audio; records communication_points; explain a solution/design of the skill aloud, recorded; score clarity, structure, pacing | communication_points >= 70 | L3 | GAP_ENGINE / THINK_ALOUD |
| `generic.pattern_drill` | PATTERN_DRILL | any | 25 | — | `PATTERN_DRILL` — timed; limit 8 min | correct >= 4 of 5 | L4 | INDEPENDENT / PATTERN_DRILL |

### Revision (`revision`)

| Key | Stage | Applies to / gap | Min | Difficulty | Observation (required evidence) | Pass criteria | Output level | Next on pass / fail |
|---|---|---|---:|---|---|---|---|---|
| `revision.problem` | REVISION | item PROBLEM | item minutes: EASY 15 / MEDIUM 25 / HARD 35 | — | `ATTEMPT` — timed; limit = item minutes | PASS, 0 hints, time <= item minutes (partial: PASS with hints or slower, or PARTIAL) | L3 | — / — |
| `revision.pattern` | REVISION | item PATTERN | 10 | — | `PATTERN_DRILL` — timed; limit 5 min | correct >= 4 of 5 (partial: correct == 3) | L4 | — / — |
| `revision.cs` | REVISION | item CS | 10 | — | `CONCEPT_EXPLAIN` | outcome_points >= 70 (partial: 50-69) | L3 | — / — |
| `revision.concept` | REVISION | item CONCEPT | 10 | — | `CONCEPT_EXPLAIN + CODE_EXERCISE` | outcome_points >= 70 (partial: 50-69) | L3 | — / — |
| `revision.sd` | REVISION | item SD | 20 | — | `SD_DESIGN + ESTIMATION_DRILL` — timed; limit 20 min | outcome_points >= 70 (partial: 50-69) | L4 | — / — |
| `revision.story` | REVISION | item BEHAVIORAL | 10 | — | `STORY_REHEARSAL` — timed; limit 3 min | outcome_points >= 70 (partial: 50-69) | L4 | — / — |
| `revision.project` | REVISION | item BEHAVIORAL | 15 | — | `PROJECT_WALKTHROUGH` — timed; limit 10 min | outcome_points >= 70 (partial: 50-69) | L4 | — / — |
| `revision.mock_weakness` | REVISION | item MOCK_WEAKNESS | 15 | — | `ITEM_DEFINED` — the component DRILL/TIMED template observation, 15-min cut | outcome_points >= 70 (partial: 50-69) | L4 | — / — |
| `revision.reinforce` | REINFORCE | item ANY | item minutes + 10 | — | `STUDY_SESSION + ITEM_DEFINED` — 10-min refresh, then the item review observation | as item type | L3 | — / — |

### Mock preparation & mocks (`mock`)

| Key | Stage | Applies to / gap | Min | Difficulty | Observation (required evidence) | Pass criteria | Output level | Next on pass / fail |
|---|---|---|---:|---|---|---|---|---|
| `mock.round` | SIMULATE | any | round minutes + 15 review (DSA 60, CS 45, LLD 105, SD 60, BEHAVIORAL 45, PROJECT_DEEP_DIVE 45) | — | `MOCK` — records round_score, rubric, per-skill outcome_points, is_weakness | round_score >= 70 | L7 | — / — |
| `mock.prep` | SIMULATE | any | 20 | — | `STUDY_SESSION + RECALL_QUIZ` — used when the mock does not fit today's budget: review last 2 mocks' weaknesses + rubric card + 5-question warm-up; the MOCK candidate is offered again on the next day it fits | n/a | L1 | — / — |
| `mock.final_simulation` | SIMULATE | any | 160 | — | `MOCK` — is_final_simulation | every round >= 70 and mean >= 75 | L7 | — / — |
