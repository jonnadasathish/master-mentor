# Master Mentor — Master Implementation Specification V3

**File:** `docs/build/MASTER_SPEC_V3.md`  
**Purpose:** One coherent implementation program that extends the completed Master Mentor foundation into a complete end-to-end personal learning and product-company interview preparation portal.

---

## 0. IMPORTANT: CURRENT STATE

This specification starts **after the existing 12 implementation slices are complete**.

Do not rebuild the foundation.

Do not restart the project from Slice 0.

Do not replace the existing evidence, gap, revision, mentor, readiness, roadmap, calibration, backup, or plan-state architecture unless the repository audit finds a concrete implementation contradiction.

### Already completed

The repository currently treats the following as implemented:

- 12 implementation slices in `docs/build/IMPLEMENTATION_PLAN.md`
- deterministic skill graph
- evidence model
- skill state
- gap engine
- revision engine
- mentor engine
- roadmap
- readiness
- baseline/calibration
- activity/problem capture
- plan items
- starting profile
- Today experience
- UI/UX V2
- calibration navigation fix
- baseline sweep → plan-item completion fix
- backup/restore verification
- seed validation
- existing golden scenarios and regression suite

Recent decisions/fixes include:

- `D-078` — UI/UX V2
- `D-079` — empty mentor-message clause handling
- `D-080` — starting profile + calibration experience
- `D-081` — Continue Calibration state/navigation correction
- `D-082` — baseline sweep/assessment/attempt completion closes associated pending plan item

### Current quality baseline

Before beginning this specification's implementation:

- preserve the existing passing backend/frontend test suite
- preserve ruff
- preserve mypy
- preserve vue-tsc
- preserve eslint
- preserve backup/restore integrity
- preserve deterministic behavior
- preserve historical evidence integrity

The current repository report states:

- backend: 478 tests passed
- frontend: 165 tests passed
- `make check`: green

Treat those as the baseline to protect, then rerun the real repository checks rather than trusting this document.

---

# 1. PRODUCT MISSION

Master Mentor is **not a generic LMS** and is **not a Scaler clone**.

It is a:

> Personal adaptive software-engineering learning and interview-preparation operating system.

Its job is to move the user from current capability to strong product-company/SDE interview readiness through a continuous evidence-based loop.

The core loop remains:

```text
Target Role
    ↓
Skill Graph
    ↓
Learning
    ↓
Practice
    ↓
Evidence
    ↓
Skill State
    ↓
Gap Detection
    ↓
Personalized Plan
    ↓
Revision
    ↓
Timed Practice
    ↓
Mock Interview
    ↓
Readiness
    ↓
Next Gap
    ↓
Repeat
```

The system must continuously answer:

1. Where am I?
2. What do I actually know?
3. What am I weak at?
4. Why is it weak?
5. What prerequisite is missing?
6. What should I learn next?
7. How should I learn it?
8. What should I practice?
9. How do I prove understanding?
10. When should I revisit it?
11. Can I reproduce it under pressure?
12. Am I ready?
13. What should I do today?

---

# 2. CORE PRODUCT PRINCIPLE

The existing system already has a strong **intelligence layer**.

The missing layer is the **teaching and learning layer**.

We are therefore adding:

```text
                    MASTER MENTOR
                         │
        ┌────────────────┼────────────────┐
        │                │                │
      LEARN            PRACTICE        EVALUATE
        │                │                │
     Lessons          Problems          Quizzes
     Concepts         Coding            Mocks
     Examples         SQL               Interviews
     Visuals          LLD               Reviews
     Explanations     Debugging         Projects
        │                │                │
        └────────────────┼────────────────┘
                         ↓
                      EVIDENCE
                         ↓
                    SKILL ENGINE
                         ↓
                  GAP / REVISION
                         ↓
                  PERSONAL MENTOR
                         ↓
                     TODAY
```

Do not create a second competing skill system.

The existing canonical skill graph remains the single source of truth.

---

# 3. NON-NEGOTIABLE ARCHITECTURAL RULES

Preserve the existing architecture:

```text
Vue 3
  ↓
FastAPI routers
  ↓
Application services
  ↓
Pure domain engines
  ↓
Repositories
  ↓
MySQL
```

The separation remains:

### Frontend

Responsible for:

- interaction
- presentation
- timers
- forms
- navigation
- read models

Must not own scoring/business rules.

### API

Responsible for:

- validation
- authentication if introduced later
- response shaping
- routing

Must not own domain formulas.

### Services

Responsible for:

- orchestration
- transaction boundaries
- loading data
- calling pure engines
- persistence

### Domain

Responsible for:

- evidence
- skill state
- gaps
- revision
- mentor
- readiness
- deterministic learning/practice rules

### Repositories

Responsible for data access only.

---

# 4. ABSOLUTE NON-GOALS

Do NOT:

- rebuild the current foundation
- create a public multi-tenant SaaS
- add authentication unless genuinely required by a concrete deployment decision
- introduce microservices
- introduce Kubernetes
- introduce Kafka
- introduce Celery/queues without a demonstrated requirement
- introduce an LLM API for core logic
- replace deterministic mentor logic with AI-generated randomness
- create thousands of low-quality problems
- create fake educational content solely to inflate coverage
- weaken readiness gates
- change historical evidence to make current progress look better
- duplicate the skill graph
- create frontend-only business logic
- create an alternate roadmap engine
- create a generic course marketplace

---

# 5. USER PROFILE / TARGET

The existing Starting Profile and Goal system remain authoritative.

The target model must support at least:

- target role
- seniority/benchmark
- primary language
- target date
- weekly available preparation time
- weekday/weekend allocation
- declared interview round types

Example:

```text
Role:
Software Engineer — Backend / Full Stack

Benchmark:
SDE-2 / strong product-company interview readiness

Primary language:
Python

Weekly budget:
10 hours

Interview loop:
DSA
CS fundamentals
Python/backend
LLD/OOD
System Design
Practical Engineering
Behavioral
Mocks
```

Do not encode company-specific guarantees.

---

# 6. LEARNING ENGINE

## 6.1 Goal

Every important skill must become actionable.

A user must never click a canonical skill and arrive at a dead end.

A skill should expose one or more of:

- Learn
- Example
- Concept Check
- Practice
- Timed Practice
- Interview Question
- Revision
- Related Practice

If a skill does not naturally map to coding problems, the UI must clearly explain why and provide concept-level practice.

---

## 6.2 Content Types

Introduce a canonical content model supporting:

1. `lesson`
2. `concept`
3. `worked_example`
4. `visual_explanation`
5. `concept_check`
6. `quiz`
7. `coding_exercise`
8. `guided_problem`
9. `timed_problem`
10. `debugging_exercise`
11. `sql_exercise`
12. `design_exercise`
13. `architecture_case`
14. `project`
15. `interview_question`
16. `behavioral_question`
17. `revision_card`

Every content item must have a stable identifier and map to one or more canonical skills.

---

## 6.3 Content Structure

A canonical learning journey should look like:

```text
Track
  ↓
Topic
  ↓
Skill
  ↓
Lesson
  ↓
Mental Model
  ↓
Worked Example
  ↓
Concept Check
  ↓
Guided Practice
  ↓
Independent Practice
  ↓
Timed Practice
  ↓
Evidence
  ↓
Revision
  ↓
Interview Application
```

Not every skill needs every stage, but every critical skill needs an actionable path.

---

# 7. LEARNING SESSION ENGINE

Introduce a structured learning session.

Example:

```text
Skill:
Binary Search

Current State:
Developing

Why:
Concept accuracy is acceptable.
Timed application is weak.
Last successful evidence is stale.

Today's session — 50 min

1. Learn                  12 min
2. Worked example          5 min
3. Concept check            5 min
4. Guided problem          10 min
5. Independent problem     15 min
6. Reflection               3 min
```

The user should not manually calculate progress.

Completion should create the appropriate evidence or assessment record.

Before/after state should be available when meaningful.

---

# 8. EMPTY-STATE / DEAD-END RULE

This is a mandatory UX rule.

Never show only:

> No problems match.

when a skill has no direct problem mapping.

The skill page must determine:

### Case A — Direct coding practice exists

Show direct problems.

### Case B — No direct problems, related problems exist

Show related problems and explain why they are related.

### Case C — Concept-oriented skill

Show:

- concept lesson
- concept check
- explanation
- related application

### Case D — Completely uncovered

Show:

- honest content-gap state
- nearest prerequisite or parent/group practice
- Developer/System content-coverage warning

The end user must still receive a meaningful next action.

---

# 9. PRACTICE ENGINE

Practice must distinguish:

```text
Seen
Attempted
Solved with help
Solved after solution
Independent solve
Timed independent solve
Interview-grade
```

Do not equate "completed" with "mastered."

Practice outcomes must flow into the existing evidence model.

---

# 10. DSA LEARNING PORTAL

Build a complete first-class DSA curriculum.

Minimum coverage:

- Arrays
- Strings
- Hashing
- Prefix Sum
- Two Pointers
- Sliding Window
- Stack
- Queue
- Linked List
- Binary Search
- Sorting
- Intervals
- Recursion
- Backtracking
- Trees
- BST
- Heap / Priority Queue
- Graphs
- BFS
- DFS
- Topological Sort
- Union Find
- Greedy
- Dynamic Programming
- Bit Manipulation
- Tries
- Monotonic Stack
- Complexity Analysis
- Problem-solving methodology
- Advanced pattern recognition

Every major topic needs:

- explanation
- mental model
- example
- common mistakes
- complexity
- concept checks
- practice
- timed practice
- interview questions
- revision material

---

# 11. DSA PROBLEM BANK

Extend the existing problem seed without destroying stable IDs.

Each problem should support metadata such as:

- stable problem ID
- title
- difficulty
- pattern
- skills
- expected time
- expected complexity
- prerequisites
- hints
- common mistakes
- interview relevance

Attempt states:

- not_started
- attempted
- failed
- solved_with_hint
- solved_after_solution
- independent_solve
- timed_solve
- needs_revision
- interview_grade

The first release can remain intentionally curated.

Do not bulk-load low-quality content.

---

# 12. COMPLEXITY / CONCEPT SKILLS

Complexity analysis is the canonical example of a concept-oriented skill.

It should teach:

- Big-O
- Big-Theta intuition
- Big-Omega intuition where relevant
- loop analysis
- nested loops
- logarithmic behavior
- recursion complexity
- space complexity
- auxiliary space
- amortized reasoning
- tradeoffs

Provide exercises such as:

```text
Analyze this loop.
Analyze this nested loop.
Analyze this recursion.
Compare two implementations.
Predict complexity before seeing the answer.
Explain your reasoning verbally.
```

This proves the skill without requiring every item to be a LeetCode-style problem.

---

# 13. PYTHON INTERVIEW TRACK

Build structured learning for:

- Python syntax
- core data structures
- functions
- scope
- closures
- iterators
- generators
- decorators
- context managers
- exceptions
- type hints
- dataclasses
- OOP
- inheritance
- composition
- protocols
- mutability
- references
- shallow/deep copy
- memory model
- performance
- threading
- multiprocessing
- asyncio
- async programming
- pytest
- mocking
- packaging
- virtual environments
- dependency management
- HTTP clients
- FastAPI
- Django
- SQL integration

Each major skill should support:

```text
Learn → Practice → Test → Interview
```

---

# 14. CS FUNDAMENTALS

## Database

Include:

- relational model
- keys
- normalization
- joins
- indexes
- B-tree
- query plans
- EXPLAIN
- transactions
- ACID
- isolation
- locks
- deadlocks
- replication
- partitioning
- sharding
- SQL optimization
- caching
- Redis concepts

## Operating Systems

Include:

- process
- thread
- scheduling
- memory
- stack/heap
- synchronization
- mutex/lock
- deadlocks
- IPC
- file systems

## Networking

Include:

- TCP/IP
- DNS
- HTTP
- HTTPS
- TLS
- REST
- WebSockets
- proxies
- load balancing
- connection lifecycle

## OOP

Include:

- abstraction
- encapsulation
- inheritance
- composition
- polymorphism
- SOLID
- cohesion
- coupling

## Testing

Include:

- unit tests
- integration tests
- contract tests
- mocks
- test strategy
- debugging

---

# 15. LLD / OOD

Progression:

```text
OOP
 ↓
Design Principles
 ↓
SOLID
 ↓
Object Relationships
 ↓
Design Patterns
 ↓
Responsibility Assignment
 ↓
Class Design
 ↓
Extensibility
 ↓
Timed LLD
 ↓
Interview
```

Use case studies such as:

- Parking Lot
- Elevator
- Library
- Vending Machine
- Notification System
- Payment System
- Inventory System
- Ride Booking
- Chess
- Splitwise-like system

Evaluate:

- requirement clarification
- responsibilities
- abstractions
- extensibility
- tradeoffs
- edge cases
- testability

---

# 16. SYSTEM DESIGN

Build progressively.

## Fundamentals

- requirements
- functional requirements
- non-functional requirements
- APIs
- data modeling
- capacity estimation

## Scaling

- load balancing
- caching
- queues
- async processing
- rate limiting
- storage
- replication

## Distributed systems

- partitioning
- sharding
- consistency
- failure handling
- reliability
- observability

## Full designs

At minimum:

- URL Shortener
- Chat System
- Food Delivery
- Ride Booking
- Notification Platform
- Video Platform
- Job Queue
- Payment System
- Social Feed
- Inventory System

Every exercise evaluates:

- requirements
- APIs
- data model
- architecture
- scalability
- reliability
- consistency
- bottlenecks
- tradeoffs
- failure modes
- observability

---

# 17. PRACTICAL ENGINEERING

Add realistic engineering exercises.

Examples:

### Performance

"API latency increased from 200ms to 2s. Diagnose it."

### Database

"Query scans millions of rows. Find the cause and propose indexes."

### Cache

"Inventory API returns stale values after write."

### Production

"API intermittently returns 500."

### Memory

"Memory grows continuously during normal traffic."

### Deployment

"CI is green but production deployment fails."

### Code review

Review a realistic pull request and identify:

- correctness risks
- scalability risks
- security issues
- testing gaps
- maintainability problems

The goal is engineering judgment.

---

# 18. PROJECT LEARNING

The portal must eventually support serious projects.

Initial flagship projects should include:

1. Inventory Management System
2. URL Shortener
3. Notification Platform
4. Job Queue
5. Payment/Order System
6. Social Feed or Messaging System

At least one flagship project must integrate:

- Vue
- Python
- FastAPI and/or Django
- MySQL
- Redis concepts
- Docker
- AWS concepts
- authentication/authorization
- caching
- background processing
- logging
- testing
- CI/CD

Every project needs:

- requirements
- architecture
- schema
- APIs
- milestones
- testing
- deployment
- observability
- failure scenarios
- interview defense questions

Project activity must produce evidence where appropriate.

---

# 19. BEHAVIORAL

Build evidence-based behavioral preparation.

Support:

- STAR
- ownership
- conflict
- disagreement
- failure
- ambiguity
- deadlines
- debugging pressure
- customer impact
- learning
- mentoring

Every story records:

```text
Situation
Task
Action
Result
Metrics
Tradeoffs
Reflection
```

Add timed rehearsal and deterministic follow-up question templates.

---

# 20. MOCK INTERVIEWS

Support:

1. Concept round
2. DSA coding round
3. CS fundamentals
4. Python/backend
5. LLD/OOD
6. System Design
7. Practical Engineering
8. Behavioral
9. Full mock

Capture:

- prompt
- time
- outcome
- hints
- mistakes
- communication
- completeness
- confidence
- follow-up handling
- evaluator notes

Mock evidence must flow into the existing readiness/evidence system.

Preserve the current rule that strong readiness cannot be achieved by hiding weak round types behind an average.

---

# 21. ADAPTIVE MENTOR

Do not replace the existing deterministic mentor.

Extend it.

Candidate selection must consider:

- skill state
- role importance
- evidence quality
- recency
- failure pressure
- prerequisites
- available time
- revision pressure
- deadline pressure
- recent performance

Rules:

```text
UNMEASURED
    → calibration / baseline assessment

WEAK
    → build

DEVELOPING
    → consolidate

STRONG + RECENT
    → maintain

STRONG + LAPSED
    → revise

BLOCKED BY PREREQUISITE
    → address prerequisite first
```

Never:

- start from Arrays just because Arrays are conventional
- start from the weakest raw number without prerequisite analysis
- repeatedly teach already-strong skills
- recommend a hard downstream exercise when a missing prerequisite explains the weakness

---

# 22. TODAY

Today is the primary user experience.

The page should answer within seconds:

```text
Good morning.

Day N
Phase: BUILD

Readiness
NOT READY

Top gap
Graph traversal

Why
Weak DFS foundation is blocking graph performance.

Today's mission

1. DFS mental model — 15 min
2. Recursion practice — 20 min
3. Graph traversal — 25 min
4. Revision — 15 min

Total
75 / 90 min

Mentor
"Do not start advanced graph problems yet. Strengthen DFS first."

Weekly
...
```

Do not turn Today into a dashboard full of unrelated widgets.

---

# 23. ROADMAP

The roadmap must be derived from:

- role
- benchmark
- target date
- weekly time
- skill graph
- evidence
- gaps
- prerequisites
- revision
- readiness

Every item should support:

> Why is this now?

Example:

```text
Graph BFS is weak.

Recursion/DFS prerequisite is also weak.

Therefore:
Recursion/DFS fundamentals
→ Tree traversal
→ Graph BFS/DFS
→ Timed graph problems
```

The roadmap must change when evidence changes.

---

# 24. REVISION

Revision is memory recovery.

Revision candidates include:

- failed problem
- slow problem
- hinted problem
- forgotten concept
- poor quiz result
- mock weakness
- lapsed skill
- repeated mistake

Support:

```text
Recall
Explain
Apply
Timed Apply
```

Respect the existing revision capacity cap.

Do not create an impossible backlog.

---

# 25. READINESS

Keep gate-based readiness.

At minimum readiness must consider:

- DSA
- CS
- Python/backend
- LLD/OOD
- System Design
- Practical Engineering
- Behavioral
- Interview execution

A strong weighted average must not hide one dangerously weak component.

Headline should remain:

```text
NOT_READY
APPROACHING
SIMULATION_ELIGIBLE
READY
LAPSED
```

The UI should show blockers, not only one percentage.

Do not claim guaranteed hiring.

---

# 26. CONTENT COVERAGE AUDIT

Create a developer-facing deterministic report:

```text
skill_id
skill_name
track
importance
direct_learning_content
concept_checks
practice_count
timed_practice
revision_content
mock_coverage
coverage_state
```

Coverage states:

- FULL
- PARTIAL
- UNMEASURED
- CONTENT_GAP

A critical skill must not be silently uncovered.

---

# 27. SEED / CONTENT AUTHORING

Keep canonical YAML/seed architecture.

Prefer:

```text
seed/
  skills.yaml
  problems.yaml
  roadmap.yaml
  mission_templates.yaml
  role_profiles/
  learning/
     lessons.yaml
     concepts.yaml
     concept_checks.yaml
     exercises.yaml
```

Do not duplicate stable skill IDs.

Every seed item must be validated before import.

Repeated seed validation/import must be deterministic.

---

# 28. DATABASE PRINCIPLES

Use migrations.

Do not bypass application services with controller-specific SQL.

Preserve authoritative append-only activity where already established.

Derived state should remain rebuildable where current architecture defines it as derived.

Do not rewrite historical evidence to satisfy current UX.

Any new content/activity relationship must be traceable.

---

# 29. API PRINCIPLES

Follow the current API architecture.

Add APIs only where necessary.

Potential new read/write surfaces include:

```text
learning content
skill learning detail
lesson progress
concept checks
learning sessions
practice recommendations
content coverage
project milestones
behavioral rehearsal
mock exercises
```

Keep routers thin.

Keep business logic in services/domain.

Responses should provide enough context for the UI to explain:

- current state
- recommendation
- reason
- evidence change

---

# 30. UX RULES

Every page must work at:

- 1280x720
- 1440x900
- 1920x1080
- 390x844

Must have:

- keyboard navigation
- accessible controls
- no horizontal overflow
- useful loading states
- useful error states
- useful empty states
- clear hierarchy
- no technical IDs exposed to normal users
- progressive disclosure

Normal preparation experience must not look like an admin dashboard.

Developer/System remains for technical diagnostics.

---

# 31. TESTING STRATEGY

For every new domain concept:

```text
domain unit test
    ↓
service test
    ↓
API test
    ↓
frontend test
    ↓
browser flow
```

Protect current tests.

Add tests for at least:

### Learning

- direct lesson
- skill with multiple content items
- content completion
- evidence creation
- deterministic ordering

### Practice

- direct problem
- related problem fallback
- concept-only skill
- uncovered skill
- no duplicate recommendations

### Sessions

- start session
- resume session
- complete session
- repeat session
- failed session

### Mentor

- weak prerequisite
- strong prerequisite
- stale strong skill
- unmeasured skill
- revision pressure

### Projects

- milestone completion
- project evidence

### Mocks

- round creation
- result capture
- mock weakness
- readiness interaction

### UX

- no dead-end skill
- empty state
- responsive
- keyboard navigation

---

# 32. BROWSER ACCEPTANCE FLOW

A clean preparation environment must support this complete journey:

```text
Starting Profile
    ↓
Goal
    ↓
Calibration
    ↓
Current Skill State
    ↓
Personalized Roadmap
    ↓
Today
    ↓
Learn
    ↓
Concept Check
    ↓
Practice
    ↓
Evidence
    ↓
Skill State Change
    ↓
Revision
    ↓
Timed Practice
    ↓
LLD
    ↓
System Design
    ↓
Practical Engineering
    ↓
Behavioral
    ↓
Mock
    ↓
Readiness
```

The user must always know the next action.

---

# 33. IMPLEMENTATION PROGRAM

Do not reuse the old 12-slice checklist as if it were unfinished.

Those are already complete.

Execute the NEW learning program in this order:

## Phase A — Reconcile

1. Inspect repository.
2. Inspect current tests.
3. Inspect current migrations.
4. Inspect current seeds.
5. Inspect current content/problem coverage.
6. Inspect current docs.
7. Reconcile all recent D-078..D-082 changes.
8. Update `FINAL_AUDIT.md` baseline section only after verifying reality.
9. Produce an implementation map.
10. Do not modify behavior yet.

Deliverable:

```text
docs/build/LEARNING_IMPLEMENTATION_BASELINE.md
```

---

## Phase B — Learning Domain Foundation

Implement:

- content model
- content/skill mapping
- lesson state
- concept-check model
- learning-session model
- content seed validation
- repository/service layer
- tests

Do not yet create every curriculum page.

Deliverable:

A working vertical slice:

```text
one skill
→ lesson
→ concept check
→ completion
→ evidence
```

---

## Phase C — Skill Learning Experience

Build:

- skill detail page
- Learn tab
- Practice tab
- Test tab
- Revision tab
- related skills
- why-this-skill-matters
- current-state explanation

Fix the current dead-end behavior.

No skill should end with a useless empty state.

---

## Phase D — DSA Curriculum

Build the DSA learning portal.

Start with the highest-value patterns and foundational concepts.

Seed enough content to create a real first journey.

Do not try to fill every possible problem immediately.

Validate:

```text
learn
→ concept check
→ guided practice
→ independent problem
→ timed practice
→ evidence
→ revision
```

---

## Phase E — Python + CS

Build the structured learning tracks for:

- Python
- DBMS/SQL
- Operating Systems
- Networking
- OOP
- Testing

Ensure each track has actionable learning and evaluation.

---

## Phase F — LLD + System Design

Build:

- concepts
- worked examples
- design exercises
- timed exercises
- rubric/evidence
- mock-ready flows

---

## Phase G — Practical Engineering + Projects + Behavioral

Build:

- realistic engineering exercises
- debugging scenarios
- project milestones
- project defense
- behavioral stories
- rehearsal

---

## Phase H — Mock Interviews

Integrate all tracks into mock rounds.

Ensure mock failures become actionable evidence/gaps.

---

## Phase I — Mentor + Roadmap Integration

Extend the current mentor rather than replacing it.

The mentor must now be capable of choosing:

```text
Learn
Practice
Review
Test
Timed
Mock
Project
Behavioral
```

based on existing deterministic gap/priority logic.

---

## Phase J — Today Integration

Today must become the orchestrator of the complete learning engine.

Example:

```text
Today's priority:
Recursion foundation

Mission:
1. Learn lesson — 15m
2. Concept check — 10m
3. Tree traversal exercise — 20m
4. Revision — 15m
5. Timed problem — 25m
```

---

## Phase K — Coverage + Readiness

Build:

- content coverage report
- learning coverage
- evidence coverage
- readiness integration
- blocker explanation

---

## Phase L — UX Hardening

Validate:

- responsive
- accessibility
- navigation
- loading
- error states
- empty states
- keyboard
- no console errors
- no horizontal overflow

---

## Phase M — Final Audit

Produce:

```text
docs/build/FINAL_AUDIT.md
docs/build/LEARNING_IMPLEMENTATION_BASELINE.md
docs/domain/LEARNING_ENGINE.md
docs/domain/CONTENT_AUTHORING_GUIDE.md
```

Update relevant:

- API docs
- UI docs
- data model
- decision log
- project context
- roadmap
- build plan

---

# 34. EXECUTION BEHAVIOR FOR CLAUDE

You are authorized to execute the whole program in dependency order.

Do not stop after every phase asking for confirmation.

For each phase:

1. inspect
2. implement
3. test
4. fix
5. document
6. continue

Stop only for a true blocker that cannot be safely resolved from repository evidence.

Do not invent requirements.

Do not silently change established scoring/readiness formulas.

If a design choice is needed:

- choose the simplest deterministic approach consistent with current architecture
- document it in `DECISION_LOG.md`
- add tests
- continue

---

# 35. QUALITY GATES

After each meaningful phase run the most relevant focused tests.

After every major integration:

```text
backend tests
frontend tests
ruff
mypy
vue-tsc
eslint
```

At final completion:

```bash
make check
```

If the project uses its Docker wrapper instead of host `make`, use the repository-supported equivalent.

Final browser check must include:

- 1280x720
- 1440x900
- 1920x1080
- 390x844

No known console errors.

No broken critical route.

No broken migration.

No content dead end for a critical skill.

No backup regression.

---

# 36. BACKUP / RESET SAFETY

Never run a destructive preparation reset during implementation without explicit need.

Before implementation changes:

```text
backup
backup verify
```

After schema/content changes:

```text
migration test
seed validation
backup verification
```

The user's actual preparation data must not be modified merely to test the new learning engine.

Use scratch/test databases for end-to-end validation.

---

# 37. FINAL CONTENT QUALITY BAR

Do not fill the portal with shallow paragraphs.

A good lesson must answer:

1. What is it?
2. Why does it exist?
3. When is it useful?
4. How does it work?
5. What is the internal model?
6. What are the tradeoffs?
7. What mistakes do engineers make?
8. How does it appear in an interview?
9. Can I demonstrate it?
10. Can I explain it?

Use practical examples.

For coding topics:

```text
concept
→ simple example
→ edge case
→ implementation
→ complexity
→ guided task
→ independent task
→ timed task
```

For system design:

```text
requirements
→ API
→ data
→ architecture
→ bottleneck
→ tradeoff
→ failure
→ observability
→ interview defense
```

For CS:

```text
concept
→ internals
→ example
→ interview question
→ misconception
→ applied question
```

---

# 38. NO FAANG GUARANTEE

Master Mentor must never claim:

- guaranteed FAANG
- guaranteed offer
- guaranteed interview
- guaranteed salary

The product promise is:

> Maximize evidence-based readiness for strong product-company software engineering interviews.

The system should be ruthless about identifying gaps, but honest about uncertainty.

---

# 39. FINAL DEFINITION OF DONE

This program is complete when a new user can:

1. enter a starting profile
2. define a goal
3. calibrate
4. see actual skill state
5. see a personalized roadmap
6. open Today
7. learn a concept
8. test understanding
9. practice
10. receive evidence
11. see skill state change
12. receive revision
13. perform timed work
14. practice DSA
15. practice Python
16. practice CS
17. practice LLD
18. practice System Design
19. practice practical engineering
20. build and defend projects
21. practice behavioral questions
22. take mocks
23. receive structured weakness feedback
24. see readiness blockers
25. repeat weak areas
26. eventually satisfy readiness gates

and at every important point:

> the application tells the user what to do next and why.

---

# 40. REQUIRED FINAL REPORT

When complete, update `docs/build/FINAL_AUDIT.md` with:

- current architecture
- current feature inventory
- current learning engine
- content counts
- skill coverage
- practice coverage
- mock coverage
- project coverage
- behavioral coverage
- migration list
- seed version/fingerprint
- tests
- browser validation
- backup/restore validation
- known limitations
- remaining content gaps
- startup commands
- reset commands
- backup commands
- daily workflow
- weekly workflow

Also include an explicit section:

```text
WHAT IS COMPLETE
WHAT IS PARTIALLY COMPLETE
WHAT REMAINS CONTENT-DEPTH WORK
WHAT MUST NOT BE CHANGED WITHOUT A NEW DECISION
```

---

# 41. FIRST CLAUDE ACTION

Before changing code, execute:

```text
1. Repository audit
2. Current state reconciliation
3. Existing content coverage report
4. Learning-domain gap analysis
5. Implementation map
```

Then begin Phase B.

Do not repeat the old 12 slices.

Do not rebuild completed foundations.

Do not stop after the audit unless a genuine blocker exists.
