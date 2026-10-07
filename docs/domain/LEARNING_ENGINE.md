# Learning Engine (MASTER_SPEC_V3, decision D-083)

Owner of: the learning layer — content catalog, completion → observation mapping, grading, learning sessions, practice resolution (the dead-end rule), derived practice states, content coverage and mock kits. Authoring format: `CONTENT_AUTHORING_GUIDE.md`. Code: `backend/app/domain/learning/` (pure), `services/learning_service.py`, `api/v1/learning.py`.

## 1. Position in the system

```text
Learn → Practice → Evaluate → Evidence → Skill state → Gap → Revision → Mentor → Today → Mock → Readiness
\_____ learning layer _____/  \_________________ existing intelligence layer (unchanged) ________________/
```

The learning layer **produces existing observations** (assessments and problem attempts) through the existing services. It adds no evidence formula, no gap, revision, mentor or readiness rule, and no second skill system: every content item maps to canonical skills of `seed/skills.yaml`.

## 2. Catalog

`seed/learning/curriculum.yaml` (tracks → topics → skills; every skill appears in at least one topic) and `seed/learning/*.yaml` content files, validated by the seed validator and loaded with the rest of the catalog (same `seed_version`, same lock). Tables: `learning_tracks`, `learning_topics`, `learning_topic_skills`, `learning_content` (type, minutes, difficulty, stages, observation kind, time limit, problem ids, validated JSON body), `learning_content_skills` (position 0 = primary skill). Content removed from the seed is deactivated, never deleted.

17 content types: lesson, concept, worked_example, visual_explanation (reading); concept_check, quiz, revision_card (checks); coding_exercise, debugging_exercise, sql_exercise, design_exercise, architecture_case, interview_question, behavioral_question (rubric practice); guided_problem, timed_problem (problem practice); project (milestones + defense).

## 3. Completion → observation (`domain/learning/evidence.py`)

| Type group | Records | Points |
|---|---|---|
| reading | `STUDY_SESSION`, `study_minutes` | none (L0) |
| concept check / quiz | `RECALL_QUIZ`, `notes_used` as declared | graded on the server (§4) |
| recall cards | `RECALL_QUIZ` | self-graded recall share |
| rubric practice | the item's declared kind (`CODE_EXERCISE`, `CONCEPT_EXPLAIN`, `LLD_DESIGN`, `MACHINE_CODING`, `SD_DESIGN`, `ESTIMATION_DRILL`, `STORY_REHEARSAL`) | rubric share; follow-up share → `followup_points` |
| project milestone | `APPLIED_TASK` (applied) on the milestone's skills | milestone rubric share |
| project defense | `PROJECT_WALKTHROUGH` on the project/behavioral skills | defense question share |
| guided / timed problem | an ordinary problem attempt (problem page or session step) | EVIDENCE_MODEL §4 |

`source_key = content:<key>` (`#<milestone>` / `#defense` for projects), so repeating the same item adds no diversity (EVIDENCE_MODEL §5.4). The first skill is the primary mapping (10000 bp), others supporting (5000 bp). `timed`, `time_limit_seconds` and `time_seconds` are sent only when the learner ran the item's timer, with the item's own limit; hints, notes and reference use are recorded as declared. The level then follows the existing ladder: a closed-book check is L1; untimed independent practice L3; timed within the limit L4; plus follow-up ≥ 70 L5.

## 4. Grading (`domain/learning/grading.py`)

Every unit earns 0, 1 or 2 halves. Choice questions: exact set match = 2, else 0 (no partial credit for multi). Short answers, recall cards, rubric criteria, follow-ups and defense questions: the learner's rating missed (0) / partly (1) / fully (2). Points = `ROUND_HALF_UP(100 × Σ halves × weight / Σ 2 × weight)`, integer 0–100. Rubric weights are the criterion points; key points and look-for points weigh 1. Pass marks: checks 60 (the recall templates' bar), rubric practice 70 (the practice templates' bar). Choice answers and explanations are not sent to the browser before grading; short questions carry their model answer for self-grading.

## 5. Learning sessions (`domain/learning/session.py`)

A session expands **one mentor stage for one skill** into steps. The stage comes from the plan item, else the gap engine's `focus_stage`, else LEARN for an unassessed skill and RECALL to maintain one on target. Slots per stage (types in preference order):

| Stage | Slots |
|---|---|
| LEARN | lesson/concept → worked example/visual → concept check/quiz → guided problem or practice item |
| DIAGNOSE | concept check/quiz → practice item or timed problem |
| RECALL / REVISION | recall cards → concept check/quiz (REVISION may use an interview question) |
| REINFORCE | recall cards or lesson → check → practice |
| GUIDED | worked example/visual → guided problem or practice item |
| INDEPENDENT | practice item (or a direct problem) |
| TIMED | timed problem or a practice item **with a time limit** (or a problem) |
| EXPLAIN / THINK_ALOUD | interview questions |
| TRANSFER / SIMULATE | project, architecture case, design or debugging exercise; interview question |

Within a slot: items made for the stage first, then items not completed yet, then the type order, then seed order. When no content fits a problem slot, a direct problem is chosen (not yet attempted first, closest to the stage's difficulty: GUIDED EASY, INDEPENDENT/TIMED MEDIUM, TRANSFER HARD). Steps are added in order while they fit the budget (the plan item's minutes); a reflection step closes LEARN/GUIDED/INDEPENDENT/TIMED/EXPLAIN/THINK_ALOUD/TRANSFER/SIMULATE sessions when it fits. At most 7 steps.

State: one ACTIVE session per skill (starting again resumes it); steps are PENDING → DONE | SKIPPED; a step records its observation and links it (`observation_type`, `observation_id`, points, passed). When no step is pending the session is COMPLETED with outcome PASSED (every scored step passed), NEEDS_REPEAT (some failed) or NOT_SCORED; ABANDONED on request. The effective score and level at the start are stored so the learner sees before/after. A session started from a plan item closes it on completion through the plan's single completion step, linked to the session's last scored observation (D-082 path). Every state change writes an `audit_log` row (`START_LEARNING_SESSION`, `COMPLETE_LEARNING_STEP`, `SKIP_LEARNING_STEP`, `COMPLETE_LEARNING_SESSION`, `ABANDON_LEARNING_SESSION`).

## 6. Practice resolution — the dead-end rule (`domain/learning/practice.py`)

| Case | When | Shown |
|---|---|---|
| DIRECT | problems map to the skill | those problems: primary mappings first, easiest first, canonical before others |
| CONCEPT | no direct problem, the skill has checks or practice items | the items, plus related problems as application |
| RELATED | dsa/coding skill, no direct problem and no own items | up to 6 problems of dependents ("uses this skill"), prerequisites ("builds the foundation") or the same group, each with its reason |
| UNCOVERED | none of the above | an honest content-gap state, the nearest prerequisite (else same-group skill) that has practice, and self-logging; the coverage report lists it |

The problem list filtered by a skill shows this resolution instead of "No problems match.".

## 7. Problem practice state

Derived from every current attempt, strongest first reached: `interview_grade` (PASS, no hints, no solution, timed within the limit, explanation ≥ 7, complexity correct — the L5 conditions) > `timed_solve` > `independent_solve` > `solved_with_hint` > `solved_after_solution` > `failed` > `attempted` > `not_started`. Completion is never shown as mastery; due revision is shown by the revision engine. Seed problems carry a `guide` (paraphrased summary, pattern, complexity, hint ladder, mistakes, prerequisites, relevance).

## 8. Progress and coverage

Progress per item is derived from the learner's current observations by `source_key` (completions, last/best points, passed, project milestones, defended). Coverage per skill (`domain/learning/coverage.py`): learning items, concept checks, practice (items + mapped problems), timed practice (items with a limit, timed problems, MEDIUM/HARD mapped problems), recall cards, the loop rounds testing its component. States: CONTENT_GAP (no learning, no checks, no practice), UNMEASURED (reading only), FULL (all five present), PARTIAL otherwise. A unit test fails if any required skill is CONTENT_GAP or UNMEASURED. Developer page: Settings → Developer → Content coverage.

## 9. Mentor, Today and mocks

The planner is unchanged. The plan read model adds `plan.learning[item_id]` — derived, not frozen — with the session a pending skill mission would open; the mission card shows its steps and "Start the session". Mock kits (`GET /learning/mock-kits`) give each round of the existing loop up to five timed prompts from the library, one per skill, ordered by the gap engine's rank, and the three required skills to probe first; results are logged with the existing mock form, whose weaknesses already feed gaps and revision. Python/backend rounds rehearse inside DSA (coding skills) and practical engineering inside the project deep dive; no new round type and no readiness change.
