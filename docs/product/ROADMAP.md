# Master Mentor — Preparation Roadmap (Spec v2)

**Machine-readable source:** [`seed/roadmap.yaml`](../../seed/roadmap.yaml). The validator checks that every one of the 133 skills appears in exactly one milestone.

The roadmap is the **order in which new topics are introduced**. It is not a schedule. Daily work is decided by the mentor from gaps (`MENTOR_ENGINE.md`). The roadmap only gates LEARN missions:
- a new topic must be in its track's current milestone or an earlier one;
- no new topic while the same track has a HIGH/CRITICAL weakness.

## 1. Structure

- **Parallel tracks**, not sequential levels. All tracks progress at the same time, so system design and behavioral don't wait months behind DSA.
- Each track has ordered **milestones**. A milestone is **complete** when every required skill in it has `level ≥ L3`, plus any extra exit criteria.
- The **current milestone** of a track is its first incomplete one.

## 2. M0 — Baseline calibration battery (first ~5 sessions)

The mentor schedules these items in order while Calibration Mode is active (`MENTOR_ENGINE.md` §3). Total ≈ 420 min.

| # | Item | Min | Observation |
|---|---|---:|---|
| B01 | Familiarity sweep: NONE/SOME/SOLID for every required skill | 15 | SELF_ASSESSMENT |
| B02 | DSA diagnostic A: arrays, hashing, two pointers, sliding window (2 unseen MEDIUM, timed) | 60 | ATTEMPT |
| B03 | Python warm-up (5 exercises, 25 min) | 30 | CODE_EXERCISE |
| B04 | CS quiz: DBMS (10 closed-book questions) | 20 | RECALL_QUIZ |
| B05 | CS quiz: OS & concurrency | 20 | RECALL_QUIZ |
| B06 | CS quiz: networking + OOP + security | 20 | RECALL_QUIZ |
| B07 | DSA diagnostic B: trees, graphs, heap | 60 | ATTEMPT |
| B08 | DSA diagnostic C: binary search, recursion/backtracking, DP | 60 | ATTEMPT |
| B09 | SD diagnostic: URL shortener, untimed, rubric per framework step | 45 | SD_DESIGN |
| B10 | LLD diagnostic: parking lot lite | 45 | LLD_DESIGN |
| B11 | Behavioral: 2 recorded answers | 20 | STORY_REHEARSAL |
| B12 | Project walkthrough, cold, recorded | 25 | PROJECT_WALKTHROUGH |

The battery can be done on paper before the app exists, and backdated into the app later.

## 3. Tracks and milestones

### `dsa_coding` — 210 min/week

| Milestone | Content | Extra exit | Volume |
|---|---|---|---|
| DSA-1 Python & foundations | Python (6), complexity, arrays, hashing, strings, two pointers, sliding window, prefix sum, linked list basics, stack, binary search basic, recursion, clarification, dry-run testing | — | ~40 problems + 20 Python exercises |
| DSA-2 Core patterns | sorting algorithms, intervals, fast/slow, monotonic stack, deque, BS boundaries + answer space, trees (traversal, paths, LCA), BST, heap (top-K, two heaps), graph traversal + grids, backtracking, greedy, design-a-DS, brute→optimal, think-aloud, bug-free coding | — | ~60 problems |
| DSA-3 Advanced | topological sort, union-find, shortest path, cycles/bipartite, MST (T4), trie, DP (fundamentals, knapsack, strings, grid, interval/state-machine T4, tree T4), bits (T4), math (T4) | — | ~45 problems |
| DSA-4 Interview execution | pattern recognition, time management, debugging under pressure, follow-ups | every T1 skill of `dsa` and `coding` at level ≥ L4 | ~25 timed/mixed problems |

Total ≈ 150–170 selected problems plus revisions. That is fewer than v1's 180–220, because the binding constraint is evidence *level* (timed, explained, transferred), not count.

### `cs` — 75 min/week

| Milestone | Content |
|---|---|
| CS-1 DBMS | SQL, modeling/normalization, indexing, query optimization, transactions, isolation/MVCC, locking/deadlocks, NoSQL trade-offs. MySQL labs. |
| CS-2 OS & concurrency | processes/threads, scheduling (T4), memory, synchronization, deadlocks, practical concurrency (thread pools, producer-consumer, asyncio, GIL). Concurrency lab. |
| CS-3 Networking, OOP, security | TCP/IP, DNS, HTTP, TLS, REST semantics, sessions/JWT/OAuth, real-time protocols, OOP principles, composition/SOLID, web security basics |

### `lld` — 75 min/week

| Milestone | Content | Extra exit |
|---|---|---|
| LLD-1 Requirements → class design | entities, use cases, classes, interfaces. Exercises: parking lot, library, LRU cache | — |
| LLD-2 Patterns & extensibility | applied patterns, change scenarios, thread safety. Exercises: elevator, splitwise, vending machine, pub-sub logger | — |
| LLD-3 Machine coding | 90-minute working, tested Python. Exercises: in-memory KV store with TTL, rate limiter class, snake & ladder, booking system | 3 MACHINE_CODING ≥ 70 on distinct exercises |

### `system_design` — 90 min/week

| Milestone | Content | Extra exit |
|---|---|---|
| SD-1 Building blocks | requirements, estimation, API, data model, HLD, caching, LB/CDN, storage/search. Systems: URL shortener, rate limiter | — |
| SD-2 Distributed systems | DB scaling, consistent hashing, queues/async, idempotency/retries, rate limiting, consistency/CAP, coordination (T4), fault tolerance, observability, security, real-time delivery. Systems: notification, chat, news feed | — |
| SD-3 Practice systems & round execution | deep dive, trade-offs, time-boxing. Systems: file storage, ride booking, food delivery, video platform, autocomplete | 6 timed SD designs ≥ 70 on distinct systems |

Design framework (rubric rows map to skills, `MISSION_LIBRARY.md` §4):
1. clarify requirements;
2. estimate;
3. API;
4. data model;
5. high-level design;
6. deep dive;
7. bottlenecks;
8. failure handling;
9. scaling;
10. trade-offs.

### `behavioral_project` — 60 min/week

| Milestone | Content | Extra exit |
|---|---|---|
| BP-1 Story bank & project brief | self-intro, ownership, impact, conflict, failure, structured answers; project architecture walkthrough + metrics | 2 stories for each competency listed in BP-1 |
| BP-2 Full coverage | ambiguity, influence, difficult decision, prioritization, why change; project trade-offs + incident story | — |
| BP-3 Follow-ups & engineering depth | follow-up handling; debugging, profiling, API engineering, testing, tooling (T4), caching practice (T4) in own codebase | — |

Story standard: STAR + direct answer first + one metric + technical depth + lesson, ≤ 3 minutes.

### `mock` — 60 min/week (from DEVELOPING or CONSOLIDATE)

| Milestone | Starts when | Exit |
|---|---|---|
| MOCK-1 Mock rounds | readiness ≥ DEVELOPING or phase ≠ BUILD | gate G6 |
| MOCK-2 Final simulations | `simulation_eligible` and a day with budget ≥ 160 | gate G9 |

Free peer-mock platforms or a friend give the non-SELF rounds G6/G9 require. Paid services are not required.

## 4. Weekly allocation (600 min)

| Track | Min/week |
|---|---:|
| dsa_coding | 210 |
| cs | 75 |
| lld | 75 |
| system_design | 90 |
| behavioral_project | 60 |
| mock | 60 |
| weekly review + buffer | 30 |

Revisions count toward the track of their skill. These minutes are soft floors (`MENTOR_ENGINE.md` §5).

## 5. Expected timeline (estimate, not a commitment)

At 10 h/week, from a mixed baseline:

| Weeks | Expected state |
|---|---|
| 1–2 | Calibration |
| 3–20 | FOUNDATION → DEVELOPING |
| ~20–32 | Mocks |
| ~30–40 | Final simulations |

That puts INTERVIEW_READY at roughly **8–10 months**. A target date sooner than this triggers CONSOLIDATE/SHARPEN parking and, if needed, `DEADLINE_INFEASIBLE`. The app's job is to make this estimate honest, not to shorten it by lowering the bar.

## 6. Learning paths (MASTER_SPEC_V3, D-083)

The milestones above order the tracks; `seed/learning/curriculum.yaml` orders the teaching inside them (tracks DSA, Python, CS fundamentals, LLD, System design, Practical engineering, Projects, Behavioral; topics in teaching order). Neither decides what comes first for a learner: the mentor's gap ranking does, prerequisites first (a weak prerequisite is taught before the downstream skill, never "Arrays because Arrays are first"). Each roadmap item's "why now" is the personal roadmap's reason plus, on the skill page, the learning session the mentor's stage opens.

### `COMM-1` Professional communication (optional, D-087)

An optional milestone on the `dsa_coding` track holding the 28 T4 `comm.*` skills. It adds no weekly minutes and never gates a milestone exit; communication practice fits in leftover time, inside technical sessions and in revision.
