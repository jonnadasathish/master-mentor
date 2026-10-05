# Content Authoring Guide (learning layer, D-083)

Owner of: the format and the quality bar of `seed/learning/*.yaml` and of the problem `guide`. The engine that uses the content is described in `LEARNING_ENGINE.md`. Seed workflow rules (versions, lock) are in `CLAUDE.md` rule 13.

## 1. Files

```text
seed/learning/
  curriculum.yaml        tracks -> topics -> canonical skills (every skill in seed/skills.yaml must appear)
  dsa_method.yaml        exemplar content file (complexity analysis, binary search) — copy its style
  <area>.yaml            any number of content files; each has `seed_version` and a `content:` list
```

The skill graph stays the only list of skills. Content maps **to** skills; it never defines one.

Validate while writing (lock errors are ignored, coverage is printed):

```bash
docker compose run --rm --no-deps -T backend python -m app.cli.catalog validate --draft --only learning/<file>.yaml
```

Release: bump `seed_version` in every seed file, `make seed-lock`, `make seed`, add a `DECISION_LOG` entry. A locked version is immutable.

## 2. Common fields

```yaml
- key: dsa.binary_search.lesson    # stable id: lower_snake segments joined by dots, at least two, <= 80 chars
  type: lesson                     # one of the 17 types in §3
  title: Binary search with an invariant you can defend
  skills: [binary_search.basic, binary_search.boundaries]   # first = primary (10000 bp), others supporting (5000 bp)
  minutes: 20                      # 1-180, realistic time for a focused learner
  difficulty: EASY                 # optional: EASY | MEDIUM | HARD
  stages: [LEARN]                  # optional; defaults per type (§4). Mentor stages this item serves
  observation: {kind: CODE_EXERCISE, time_limit_seconds: 900}   # optional; see §5
  problems: [15]                   # guided_problem / timed_problem only: seed problem ids
  body: {...}                      # type-specific, §3
```

Never change a released key: observations refer to it (`source_key = content:<key>`). Retire content by removing it from the seed; the loader deactivates it and history keeps working.

## 3. Types and their body

Text fields accept a safe subset: paragraphs (blank line), `- ` lists, `` `code` ``, `**bold**`, fenced code blocks. No HTML. `code` fields are `{language, code, explanation?}`.

| Type | Records | Body (required **bold**) |
|---|---|---|
| `lesson` | STUDY_SESSION (L0) | **summary, what, why, when, how, mental_model, tradeoffs, mistakes[], interview, explain_it[]**, example (code), complexity, internals, edge_cases[], misconceptions[] |
| `concept` | STUDY_SESSION | **summary, explanation, points[]**, example, misconceptions[] |
| `worked_example` | STUDY_SESSION | **problem, steps[{title, text, code?}] (≥2), takeaways[]**, complexity, code |
| `visual_explanation` | STUDY_SESSION | **summary, frames[{caption, diagram}] (≥2)** — diagrams are monospace text |
| `concept_check` | RECALL_QUIZ, graded by the server | intro, **questions (≥3)** |
| `quiz` | RECALL_QUIZ | intro, **questions (≥5)** |
| `revision_card` | RECALL_QUIZ, self-graded recall | **cards[{front, back}] (≥3)** |
| `coding_exercise` | CODE_EXERCISE or CONCEPT_EXPLAIN | **prompt, hints[], solution (code), rubric**, examples[], constraints[], starter (code), follow_ups |
| `debugging_exercise` | CONCEPT_EXPLAIN or CODE_EXERCISE | **scenario, symptoms[], tasks[], reference, rubric**, artifacts (text or code), hints[], solution, follow_ups |
| `sql_exercise` | CONCEPT_EXPLAIN | **prompt, schema (code), hints[], solution (code), rubric**, follow_ups |
| `design_exercise` (LLD) | LLD_DESIGN or MACHINE_CODING | **prompt, requirements{functional[], non_functional[]}, approach[], rubric, follow_ups**, hints[], reference, code |
| `architecture_case` (SD) | SD_DESIGN or ESTIMATION_DRILL | **prompt, requirements, approach[], rubric, follow_ups**, estimates, hints[], reference |
| `interview_question` | CONCEPT_EXPLAIN | **prompt, key_points[] (the rubric, 1 point each), follow_ups**, model_answer, pitfalls[] |
| `behavioral_question` | STORY_REHEARSAL | **prompt, competency, look_for[] (the rubric), follow_ups**, pitfalls[] |
| `guided_problem` | a problem attempt | **guidance[]**, hints[]; `problems: [ids]` |
| `timed_problem` | a problem attempt | **guidance[]**; `problems: [ids]` |
| `project` | APPLIED_TASK per milestone, PROJECT_WALKTHROUGH for the defense | **summary, requirements, architecture, schema, apis[], milestones (≥2), testing[], deployment[], observability[], failure_scenarios[], defense_questions[]**, stack[] |

Questions:

```yaml
questions:
  - id: q1                 # lower_snake, unique in the check
    kind: single           # single | multi | short
    prompt: What is the time complexity of this function?
    code: {language: python, code: "..."}         # optional
    options: ["O(n)", "O(log n)", "O(n log n)"]   # single/multi: ≥ 2 distinct options
    answer: [1]            # 0-based indexes; single: exactly one
    explanation: Why the right answer is right AND why the tempting wrong one is wrong.
  - id: q2
    kind: short            # self-graded against model_answer (missed / partly / fully)
    prompt: ...
    model_answer: ...
    explanation: ...
```

Rubric (`rubric`, milestone `rubric`): `[{key, label, points 1-10}]`, at least two criteria. The learner rates each criterion missed / partly / fully; `outcome_points` = weighted share (integer, ROUND_HALF_UP). Follow-ups: `[{prompt, look_for}]`; rating them gives `followup_points`, which is what lets a timed attempt reach L5 under the existing practice ladder. Project milestones: `{key, title, goal, deliverables[], skills[], minutes, rubric}`.

## 4. Stages

Default stages per type: lesson/concept/visual `LEARN`; worked example `LEARN, GUIDED`; concept check `LEARN, RECALL, DIAGNOSE`; quiz `RECALL, DIAGNOSE, REINFORCE`; revision cards `RECALL, REINFORCE, REVISION`; coding/sql exercise `GUIDED, INDEPENDENT, TIMED`; debugging `INDEPENDENT, TIMED, TRANSFER`; design/architecture `GUIDED, INDEPENDENT, TIMED, EXPLAIN`; interview question `EXPLAIN, THINK_ALOUD, TIMED, INDEPENDENT`; behavioral question `LEARN, GUIDED, INDEPENDENT, TIMED, EXPLAIN`; guided problem `GUIDED`; timed problem `INDEPENDENT, TIMED`; project `TRANSFER, SIMULATE`. A TIMED session only uses items with `observation.time_limit_seconds` (or timed problems), so give timed practice a realistic limit (interview-like: 10–20 min CS questions, 15–25 min coding, 45 min designs).

## 5. Observation kind vs skill component

Allowed components per kind (D-055, enforced by the validator):

| Kind | Components |
|---|---|
| STUDY_SESSION, RECALL_QUIZ, CONCEPT_EXPLAIN, APPLIED_TASK | any |
| CODE_EXERCISE | coding, dsa |
| ESTIMATION_DRILL | system_design |
| SD_DESIGN | system_design, cs |
| LLD_DESIGN, MACHINE_CODING | lld, coding |
| STORY_REHEARSAL | behavioral |
| PROJECT_WALKTHROUGH | project, behavioral |

So: a behavioral question maps only to behavioral skills; a coding exercise on a CS skill must declare `observation: {kind: CONCEPT_EXPLAIN}`; a project must include at least one project or behavioral skill (for its defense).

## 6. Quality bar (MASTER_SPEC_V3 §37)

A lesson answers: what is it, why it exists, when it is useful, how it works, the internal model, trade-offs, the mistakes engineers make, how it appears in an interview, how to demonstrate it (example) and how to explain it (`explain_it`). Coding topics go concept → simple example → edge case → implementation → complexity → guided → independent → timed. System design goes requirements → API → data → architecture → bottleneck → trade-off → failure → observability → interview defense. CS goes concept → internals → example → interview question → misconception → applied question.

Rules:

- Correct before complete. Every complexity, API behaviour and protocol detail must be right; when a fact depends on a version or an engine (MySQL InnoDB, CPython), say which.
- Concrete over generic: numbers, code, a real failure mode. No filler sentences, no "it is important to note".
- Explanations teach: say why the right option is right and why the tempting one is wrong.
- Rubric criteria are observable ("states the invariant before coding"), never vague ("good answer").
- Paraphrase problems; never paste a platform's problem statement. Link by seed problem id.
- No claims about what a specific company asks; the role profile is an internal benchmark. No hiring guarantees.
- One idea per card; a card back fits on one line.

## 7. YAML pitfalls

- A list item or value containing `: ` must be quoted, or YAML reads a mapping (`- "Using X: a thing"`). The validator reports this as `learning.invalid_list`.
- Use `|-` blocks for multi-line text and code; keep indentation consistent.
- No floats anywhere in seed data.

## 8. Problem guide (`seed/problems.yaml`)

```yaml
- id: 15
  ...
  guide:
    summary: Find a target's index in a sorted array, or -1.   # a paraphrase, never the statement
    pattern: Closed-interval binary search
    time: O(log n)
    space: O(1)
    hints: [Keep lo <= hi and exclude mid in both branches.]   # a ladder, weakest hint first
    mistakes: [hi = mid inside while lo <= hi loops forever]
    prerequisites: [arrays.traversal]                          # optional, known skill keys
    relevance: HIGH                                            # HIGH | MEDIUM | LOW interview relevance
```

New seed problems take the next free id (ids are stable forever; personal problems start at 1,000,000), exactly one primary (10000) skill mapping and the platform's exact slug.
