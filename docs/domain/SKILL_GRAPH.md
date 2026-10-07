# Master Mentor — Skill Graph (Spec v2, `seed-v1`)

**Machine-readable source:** [`seed/skills.yaml`](../../seed/skills.yaml) (graph) + [`seed/role_profiles/backend_fullstack_sde2.yaml`](../../seed/role_profiles/backend_fullstack_sde2.yaml) (`skill_tiers`).

The tables below are generated from the same data. If they disagree with the YAML, the YAML wins.

## 1. Structure rules

1. **Two node kinds.**
   - **Skill groups** (22) are non-scored parents.
   - **Skills** (133) are scored and gap-bearing.
   - **Topics** are free-text tags inside a skill, never scored.
2. **One key per concept.** No concept appears in two components:
   - replication, sharding and partitioning live only in `sd.database_scaling`;
   - LB/CDN live only in `sd.load_balancing_cdn`;
   - design patterns live only in `lld.design_patterns`;
   - engineering testing (`testing.*`, component `project`) is distinct from interview dry-run testing (`execution.testing_dry_run`, component `coding`).
3. **Prerequisites are the only relationship.** An edge "A requires B at `min_score`" is satisfied when `B.score ≥ min_score` (`GLOSSARY.md`).
   - Allowed `min_score` values: **30** (guided exposure), **45** (independent), **60** (timed).
4. **Tiers come from the role profile**, not the graph:
   - T1: importance 100, target 80, floor 65
   - T2: importance 75, target 75, floor 55
   - T3: importance 50, target 65, no floor
   - T4: importance 20, target 50, no floor; optional
5. **Every skill has exactly one component.**
6. **Evidence kinds** are *descriptive* metadata: the observation kinds the UI offers first for the skill. They are **not enforced**. Any observation that names a skill (problem mapping, assessment skill row, mock round skill row, derivation rule) produces evidence for it. Legend:
   - `A` problem attempt
   - `R` recall quiz
   - `PD` pattern drill
   - `P` practice (explain / design / story / walkthrough / exercise)
   - `T` timed practice
   - `F` follow-up / trade-off rubric
   - `AP` applied task
   - `M` mock round

   Interview-execution skills also receive derived rows from attempt rubrics and mistake routing (`EVIDENCE_MODEL.md` §5.2–5.3).

## 2. Validation (seed validator: `make seed-validate`, also run by every `make seed`)

| Check | Result for `seed-v1` |
|---|---|
| Unique skill keys | pass (133) |
| Every parent is a known group | pass (22 groups) |
| Every prerequisite key exists | pass |
| Prerequisite graph acyclic (Kahn's algorithm) | **pass**: 31 roots, maximum depth 6 |
| `min_score ∈ {30, 45, 60}` and `min_score ≤ prerequisite target` | pass |
| No required (T1–T3) skill depends on an optional (T4) skill | pass |
| Every component `gate ≤ importance-weighted target mean` | pass (see `ROLE_PROFILE.md` §3) |

Root skills (no prerequisites; cold-start diagnostics begin here):
`python.core_syntax`, `execution.clarification`, `execution.think_aloud`, `execution.testing_dry_run`, `execution.time_management`, `dsa.complexity_analysis`, `bit_manipulation.core`, `math.number_basics`, `db.sql_querying`, `os.processes_threads`, `network.tcp_ip_udp`, `oop.principles`, `lld.requirements_entities`, `sd.requirements_scoping`, `sd.capacity_estimation`, `sd.observability`, `sd.time_boxing`, `behavioral.self_introduction`, `behavioral.ownership`, `behavioral.impact`, `behavioral.conflict_disagreement`, `behavioral.failure_learning`, `behavioral.ambiguity`, `behavioral.influence_leadership`, `behavioral.difficult_decision`, `behavioral.prioritization`, `communication.structured_answers`, `project.architecture_walkthrough`, `engineering.debugging`, `engineering.tooling`, `testing.unit_integration`

## 3. Counts

| Component | T1 | T2 | T3 | T4 | Total | Required |
|---|---:|---:|---:|---:|---:|---:|
| `dsa` | 11 | 21 | 7 | 5 | 44 | 39 |
| `coding` | 2 | 6 | 5 | 1 | 14 | 13 |
| `cs` | 6 | 10 | 7 | 1 | 24 | 23 |
| `lld` | 3 | 2 | 1 | 0 | 6 | 6 |
| `system_design` | 8 | 8 | 5 | 1 | 22 | 21 |
| `behavioral` | 3 | 6 | 3 | 0 | 12 | 12 |
| `project` | 2 | 3 | 4 | 2 | 11 | 9 |
| **Total** | **35** | **56** | **32** | **10** | **133** | **123** |

## 4. Skills by component and group

### Component `dsa` — DSA


#### Group `dsa.foundations` — DSA foundations & array patterns

| Skill key | Tier | Imp | Target | Floor | Prerequisites (min score) | Evidence | Pattern |
|---|---|---:|---:|---:|---|---|---|
| `dsa.complexity_analysis` | T1 | 100 | 80 | 65 | — | A R M |  |
| `arrays.traversal` | T2 | 75 | 75 | 55 | `python.core_syntax` ≥30 | A R PD M | yes |
| `hashing.lookup_frequency` | T1 | 100 | 80 | 65 | `arrays.traversal` ≥45, `python.collections` ≥30 | A R PD M | yes |
| `strings.manipulation` | T2 | 75 | 75 | 55 | `arrays.traversal` ≥45 | A R PD M | yes |
| `two_pointers.core` | T1 | 100 | 80 | 65 | `arrays.traversal` ≥45 | A R PD M | yes |
| `sliding_window.core` | T1 | 100 | 80 | 65 | `two_pointers.core` ≥45, `hashing.lookup_frequency` ≥45 | A R PD M | yes |
| `prefix_sum.core` | T2 | 75 | 75 | 55 | `arrays.traversal` ≥45, `hashing.lookup_frequency` ≥45 | A R PD M | yes |
| `sorting.algorithms` | T3 | 50 | 65 | — | `arrays.traversal` ≥45, `dsa.complexity_analysis` ≥30 | A R PD M | yes |
| `intervals.core` | T2 | 75 | 75 | 55 | `python.sorting_keys` ≥30, `arrays.traversal` ≥45 | A R PD M | yes |

#### Group `dsa.linear` — Linear structures & binary search

| Skill key | Tier | Imp | Target | Floor | Prerequisites (min score) | Evidence | Pattern |
|---|---|---:|---:|---:|---|---|---|
| `linked_list.manipulation` | T2 | 75 | 75 | 55 | `python.core_syntax` ≥30 | A R PD M | yes |
| `linked_list.fast_slow` | T3 | 50 | 65 | — | `linked_list.manipulation` ≥45 | A R PD M | yes |
| `stack.basic` | T2 | 75 | 75 | 55 | `arrays.traversal` ≥45 | A R PD M | yes |
| `stack.monotonic` | T2 | 75 | 75 | 55 | `stack.basic` ≥45 | A R PD M | yes |
| `queue.deque` | T3 | 50 | 65 | — | `stack.basic` ≥30 | A R PD M | yes |
| `binary_search.basic` | T1 | 100 | 80 | 65 | `arrays.traversal` ≥45 | A R PD M | yes |
| `binary_search.boundaries` | T2 | 75 | 75 | 55 | `binary_search.basic` ≥60 | A R PD M | yes |
| `binary_search.answer_space` | T2 | 75 | 75 | 55 | `binary_search.boundaries` ≥45 | A R PD M | yes |

#### Group `dsa.trees_heaps` — Recursion, trees, tries, heaps

| Skill key | Tier | Imp | Target | Floor | Prerequisites (min score) | Evidence | Pattern |
|---|---|---:|---:|---:|---|---|---|
| `recursion.fundamentals` | T1 | 100 | 80 | 65 | `python.core_syntax` ≥30 | A R M |  |
| `trees.traversal` | T1 | 100 | 80 | 65 | `recursion.fundamentals` ≥45 | A R PD M | yes |
| `trees.path_depth` | T2 | 75 | 75 | 55 | `trees.traversal` ≥60 | A R PD M | yes |
| `trees.lca_construction` | T3 | 50 | 65 | — | `trees.traversal` ≥45 | A R PD M | yes |
| `bst.operations` | T2 | 75 | 75 | 55 | `trees.traversal` ≥45, `binary_search.basic` ≥45 | A R PD M | yes |
| `trie.core` | T3 | 50 | 65 | — | `trees.traversal` ≥45, `hashing.lookup_frequency` ≥45 | A R PD M | yes |
| `heap.top_k` | T1 | 100 | 80 | 65 | `python.collections` ≥45, `dsa.complexity_analysis` ≥30 | A R PD M | yes |
| `heap.two_heaps_merge_k` | T3 | 50 | 65 | — | `heap.top_k` ≥60 | A R PD M | yes |

#### Group `dsa.graphs` — Graphs

| Skill key | Tier | Imp | Target | Floor | Prerequisites (min score) | Evidence | Pattern |
|---|---|---:|---:|---:|---|---|---|
| `graph.traversal` | T1 | 100 | 80 | 65 | `trees.traversal` ≥45, `hashing.lookup_frequency` ≥45, `queue.deque` ≥30 | A R PD M | yes |
| `graph.grid_multisource` | T2 | 75 | 75 | 55 | `graph.traversal` ≥60 | A R PD M | yes |
| `graph.topological_sort` | T2 | 75 | 75 | 55 | `graph.traversal` ≥60 | A R PD M | yes |
| `graph.union_find` | T2 | 75 | 75 | 55 | `graph.traversal` ≥45 | A R PD M | yes |
| `graph.shortest_path` | T2 | 75 | 75 | 55 | `graph.traversal` ≥60, `heap.top_k` ≥45 | A R PD M | yes |
| `graph.cycles_bipartite` | T3 | 50 | 65 | — | `graph.traversal` ≥45 | A R PD M | yes |
| `graph.mst` | T4 | 20 | 50 | — | `graph.union_find` ≥45, `heap.top_k` ≥45 | A R PD M | yes |

#### Group `dsa.search_dp` — Backtracking, greedy, dynamic programming

| Skill key | Tier | Imp | Target | Floor | Prerequisites (min score) | Evidence | Pattern |
|---|---|---:|---:|---:|---|---|---|
| `backtracking.core` | T2 | 75 | 75 | 55 | `recursion.fundamentals` ≥60 | A R PD M | yes |
| `greedy.core` | T2 | 75 | 75 | 55 | `python.sorting_keys` ≥30, `dsa.complexity_analysis` ≥30 | A R PD M | yes |
| `dp.fundamentals` | T1 | 100 | 80 | 65 | `recursion.fundamentals` ≥60 | A R PD M | yes |
| `dp.knapsack_subset` | T2 | 75 | 75 | 55 | `dp.fundamentals` ≥60 | A R PD M | yes |
| `dp.strings_subsequence` | T2 | 75 | 75 | 55 | `dp.fundamentals` ≥60, `strings.manipulation` ≥45 | A R PD M | yes |
| `dp.grid_paths` | T2 | 75 | 75 | 55 | `dp.fundamentals` ≥45 | A R PD M | yes |
| `dp.interval_state_machine` | T4 | 20 | 50 | — | `dp.fundamentals` ≥60 | A R PD M | yes |
| `dp.tree` | T4 | 20 | 50 | — | `dp.fundamentals` ≥60, `trees.path_depth` ≥45 | A R PD M | yes |

#### Group `dsa.misc` — Bits, math, data-structure design, recognition

| Skill key | Tier | Imp | Target | Floor | Prerequisites (min score) | Evidence | Pattern |
|---|---|---:|---:|---:|---|---|---|
| `bit_manipulation.core` | T4 | 20 | 50 | — | — | A R PD M | yes |
| `math.number_basics` | T4 | 20 | 50 | — | — | A R M |  |
| `design_ds.core` | T2 | 75 | 75 | 55 | `hashing.lookup_frequency` ≥45, `linked_list.manipulation` ≥45 | A R PD M | yes |
| `dsa.pattern_recognition` | T1 | 100 | 80 | 65 | `hashing.lookup_frequency` ≥45, `two_pointers.core` ≥45 | A PD M |  |

### Component `coding` — Coding & Execution


#### Group `lang.python` — Python (interview language)

| Skill key | Tier | Imp | Target | Floor | Prerequisites (min score) | Evidence | Pattern |
|---|---|---:|---:|---:|---|---|---|
| `python.core_syntax` | T2 | 75 | 75 | 55 | — | A R P T |  |
| `python.collections` | T2 | 75 | 75 | 55 | `python.core_syntax` ≥45 | A R P T |  |
| `python.sorting_keys` | T3 | 50 | 65 | — | `python.core_syntax` ≥45 | A R P T |  |
| `python.oop` | T3 | 50 | 65 | — | `python.core_syntax` ≥45 | A R P T |  |
| `python.iterators_generators` | T4 | 20 | 50 | — | `python.core_syntax` ≥45 | A R P T |  |
| `python.builtin_complexity` | T3 | 50 | 65 | — | `python.collections` ≥45, `dsa.complexity_analysis` ≥30 | A R P T |  |

#### Group `coding.execution` — Interview execution (coding rounds)

| Skill key | Tier | Imp | Target | Floor | Prerequisites (min score) | Evidence | Pattern |
|---|---|---:|---:|---:|---|---|---|
| `execution.clarification` | T2 | 75 | 75 | 55 | — | A R P T M |  |
| `execution.brute_force_to_optimal` | T1 | 100 | 80 | 65 | `dsa.complexity_analysis` ≥45 | A R P T M |  |
| `execution.think_aloud` | T2 | 75 | 75 | 55 | — | A R P T M |  |
| `execution.bug_free_coding` | T1 | 100 | 80 | 65 | `python.collections` ≥45 | A R P T M |  |
| `execution.testing_dry_run` | T2 | 75 | 75 | 55 | — | A R P T M |  |
| `execution.time_management` | T2 | 75 | 75 | 55 | — | A R P T M |  |
| `execution.debugging_under_pressure` | T3 | 50 | 65 | — | `execution.testing_dry_run` ≥30 | A R P T M |  |
| `execution.followup_handling` | T3 | 50 | 65 | — | `execution.brute_force_to_optimal` ≥45 | A R P T M |  |

### Component `cs` — CS Fundamentals


#### Group `cs.dbms` — DBMS

| Skill key | Tier | Imp | Target | Floor | Prerequisites (min score) | Evidence | Pattern |
|---|---|---:|---:|---:|---|---|---|
| `db.sql_querying` | T1 | 100 | 80 | 65 | — | R P T F AP M |  |
| `db.modeling_normalization` | T2 | 75 | 75 | 55 | `db.sql_querying` ≥45 | R P T F AP M |  |
| `db.indexing` | T1 | 100 | 80 | 65 | `db.sql_querying` ≥45 | R P T F AP M |  |
| `db.query_optimization` | T2 | 75 | 75 | 55 | `db.indexing` ≥60 | R P T F AP M |  |
| `db.transactions_acid` | T1 | 100 | 80 | 65 | `db.sql_querying` ≥45 | R P T F AP M |  |
| `db.isolation_mvcc` | T2 | 75 | 75 | 55 | `db.transactions_acid` ≥60 | R P T F AP M |  |
| `db.locking_deadlocks` | T2 | 75 | 75 | 55 | `db.transactions_acid` ≥60 | R P T F AP M |  |
| `db.nosql_tradeoffs` | T3 | 50 | 65 | — | `db.modeling_normalization` ≥45 | R P T F AP M |  |

#### Group `cs.os` — Operating systems & concurrency

| Skill key | Tier | Imp | Target | Floor | Prerequisites (min score) | Evidence | Pattern |
|---|---|---:|---:|---:|---|---|---|
| `os.processes_threads` | T1 | 100 | 80 | 65 | — | R P T F AP M |  |
| `os.scheduling_context_switch` | T4 | 20 | 50 | — | `os.processes_threads` ≥45 | R P T F AP M |  |
| `os.memory_virtual` | T3 | 50 | 65 | — | `os.processes_threads` ≥45 | R P T F AP M |  |
| `os.synchronization` | T1 | 100 | 80 | 65 | `os.processes_threads` ≥45 | R P T F AP M |  |
| `os.deadlocks` | T3 | 50 | 65 | — | `os.synchronization` ≥45 | R P T F AP M |  |
| `os.concurrency_practical` | T2 | 75 | 75 | 55 | `os.synchronization` ≥45, `python.core_syntax` ≥45 | R P T F AP M |  |

#### Group `cs.networking` — Networking

| Skill key | Tier | Imp | Target | Floor | Prerequisites (min score) | Evidence | Pattern |
|---|---|---:|---:|---:|---|---|---|
| `network.tcp_ip_udp` | T2 | 75 | 75 | 55 | — | R P T F AP M |  |
| `network.dns` | T3 | 50 | 65 | — | `network.tcp_ip_udp` ≥30 | R P T F AP M |  |
| `network.http` | T1 | 100 | 80 | 65 | `network.tcp_ip_udp` ≥30 | R P T F AP M |  |
| `network.tls_https` | T3 | 50 | 65 | — | `network.http` ≥45, `network.tcp_ip_udp` ≥45 | R P T F AP M |  |
| `network.rest_semantics` | T2 | 75 | 75 | 55 | `network.http` ≥45 | R P T F AP M |  |
| `network.sessions_auth` | T2 | 75 | 75 | 55 | `network.http` ≥45 | R P T F AP M |  |
| `network.realtime_protocols` | T3 | 50 | 65 | — | `network.http` ≥45, `network.tcp_ip_udp` ≥45 | R P T F AP M |  |

#### Group `cs.oop` — OOP

| Skill key | Tier | Imp | Target | Floor | Prerequisites (min score) | Evidence | Pattern |
|---|---|---:|---:|---:|---|---|---|
| `oop.principles` | T2 | 75 | 75 | 55 | — | R P T F AP M |  |
| `oop.composition_solid` | T2 | 75 | 75 | 55 | `oop.principles` ≥45 | R P T F AP M |  |

#### Group `cs.security` — Security basics

| Skill key | Tier | Imp | Target | Floor | Prerequisites (min score) | Evidence | Pattern |
|---|---|---:|---:|---:|---|---|---|
| `security.web_basics` | T3 | 50 | 65 | — | `network.sessions_auth` ≥45 | R P T F AP M |  |

### Component `lld` — LLD / OOD


#### Group `lld.design` — LLD / OOD / machine coding

| Skill key | Tier | Imp | Target | Floor | Prerequisites (min score) | Evidence | Pattern |
|---|---|---:|---:|---:|---|---|---|
| `lld.requirements_entities` | T1 | 100 | 80 | 65 | — | R P T F AP M |  |
| `lld.class_design` | T1 | 100 | 80 | 65 | `oop.principles` ≥45, `lld.requirements_entities` ≥45 | R P T F AP M |  |
| `lld.design_patterns` | T2 | 75 | 75 | 55 | `oop.composition_solid` ≥45 | R P T F AP M |  |
| `lld.extensibility` | T2 | 75 | 75 | 55 | `lld.class_design` ≥60, `oop.composition_solid` ≥45 | R P T F AP M |  |
| `lld.concurrency_safety` | T3 | 50 | 65 | — | `lld.class_design` ≥45, `os.synchronization` ≥45 | R P T F AP M |  |
| `lld.machine_coding` | T1 | 100 | 80 | 65 | `lld.class_design` ≥60, `python.oop` ≥45, `execution.bug_free_coding` ≥45 | R P T F AP M |  |

### Component `system_design` — System Design


#### Group `sd.fundamentals` — System design fundamentals

| Skill key | Tier | Imp | Target | Floor | Prerequisites (min score) | Evidence | Pattern |
|---|---|---:|---:|---:|---|---|---|
| `sd.requirements_scoping` | T1 | 100 | 80 | 65 | — | R P T F AP M |  |
| `sd.capacity_estimation` | T2 | 75 | 75 | 55 | — | R P T F AP M |  |
| `sd.api_design` | T2 | 75 | 75 | 55 | `network.rest_semantics` ≥45 | R P T F AP M |  |
| `sd.data_modeling` | T1 | 100 | 80 | 65 | `db.modeling_normalization` ≥45, `db.indexing` ≥45 | R P T F AP M |  |
| `sd.high_level_decomposition` | T1 | 100 | 80 | 65 | `sd.requirements_scoping` ≥45 | R P T F AP M |  |
| `sd.caching` | T1 | 100 | 80 | 65 | `network.http` ≥45, `sd.high_level_decomposition` ≥30 | R P T F AP M |  |
| `sd.load_balancing_cdn` | T2 | 75 | 75 | 55 | `network.http` ≥45 | R P T F AP M |  |
| `sd.storage_search` | T3 | 50 | 65 | — | `sd.data_modeling` ≥45 | R P T F AP M |  |

#### Group `sd.distributed` — Distributed systems

| Skill key | Tier | Imp | Target | Floor | Prerequisites (min score) | Evidence | Pattern |
|---|---|---:|---:|---:|---|---|---|
| `sd.database_scaling` | T1 | 100 | 80 | 65 | `db.indexing` ≥60, `db.transactions_acid` ≥45 | R P T F AP M |  |
| `sd.consistent_hashing` | T3 | 50 | 65 | — | `sd.database_scaling` ≥45 | R P T F AP M |  |
| `sd.queues_async` | T1 | 100 | 80 | 65 | `sd.high_level_decomposition` ≥45 | R P T F AP M |  |
| `sd.idempotency_retries` | T2 | 75 | 75 | 55 | `sd.queues_async` ≥45, `network.rest_semantics` ≥45 | R P T F AP M |  |
| `sd.rate_limiting` | T2 | 75 | 75 | 55 | `sd.caching` ≥45 | R P T F AP M |  |
| `sd.consistency_cap` | T2 | 75 | 75 | 55 | `sd.database_scaling` ≥45, `db.isolation_mvcc` ≥45 | R P T F AP M |  |
| `sd.distributed_coordination` | T4 | 20 | 50 | — | `sd.consistency_cap` ≥60 | R P T F AP M |  |
| `sd.fault_tolerance` | T2 | 75 | 75 | 55 | `sd.idempotency_retries` ≥45 | R P T F AP M |  |
| `sd.observability` | T3 | 50 | 65 | — | — | R P T F AP M |  |
| `sd.security_design` | T3 | 50 | 65 | — | `security.web_basics` ≥45 | R P T F AP M |  |
| `sd.realtime_delivery` | T3 | 50 | 65 | — | `network.realtime_protocols` ≥45, `sd.queues_async` ≥45 | R P T F AP M |  |

#### Group `sd.execution` — System design round execution

| Skill key | Tier | Imp | Target | Floor | Prerequisites (min score) | Evidence | Pattern |
|---|---|---:|---:|---:|---|---|---|
| `sd.deep_dive_bottlenecks` | T1 | 100 | 80 | 65 | `sd.high_level_decomposition` ≥60 | R P T F AP M |  |
| `sd.tradeoff_articulation` | T1 | 100 | 80 | 65 | `sd.high_level_decomposition` ≥45 | R P T F AP M |  |
| `sd.time_boxing` | T2 | 75 | 75 | 55 | — | R P T F AP M |  |

### Component `behavioral` — Behavioral


#### Group `beh.competencies` — Behavioral competencies

| Skill key | Tier | Imp | Target | Floor | Prerequisites (min score) | Evidence | Pattern |
|---|---|---:|---:|---:|---|---|---|
| `behavioral.self_introduction` | T2 | 75 | 75 | 55 | — | P T F AP M |  |
| `behavioral.ownership` | T1 | 100 | 80 | 65 | — | P T F AP M |  |
| `behavioral.impact` | T1 | 100 | 80 | 65 | — | P T F AP M |  |
| `behavioral.conflict_disagreement` | T2 | 75 | 75 | 55 | — | P T F AP M |  |
| `behavioral.failure_learning` | T2 | 75 | 75 | 55 | — | P T F AP M |  |
| `behavioral.ambiguity` | T2 | 75 | 75 | 55 | — | P T F AP M |  |
| `behavioral.influence_leadership` | T2 | 75 | 75 | 55 | — | P T F AP M |  |
| `behavioral.difficult_decision` | T3 | 50 | 65 | — | — | P T F AP M |  |
| `behavioral.prioritization` | T3 | 50 | 65 | — | — | P T F AP M |  |
| `behavioral.why_change` | T3 | 50 | 65 | — | `behavioral.self_introduction` ≥30 | P T F AP M |  |

#### Group `beh.communication` — Communication

| Skill key | Tier | Imp | Target | Floor | Prerequisites (min score) | Evidence | Pattern |
|---|---|---:|---:|---:|---|---|---|
| `communication.structured_answers` | T1 | 100 | 80 | 65 | — | P T F AP M |  |
| `communication.followup_handling` | T2 | 75 | 75 | 55 | `communication.structured_answers` ≥45 | P T F AP M |  |

### Component `project` — Project Deep Dive


#### Group `pdd.project` — Project / technical deep dive

| Skill key | Tier | Imp | Target | Floor | Prerequisites (min score) | Evidence | Pattern |
|---|---|---:|---:|---:|---|---|---|
| `project.architecture_walkthrough` | T1 | 100 | 80 | 65 | — | P T F AP M |  |
| `project.tradeoffs_decisions` | T1 | 100 | 80 | 65 | `project.architecture_walkthrough` ≥45 | P T F AP M |  |
| `project.metrics_impact` | T2 | 75 | 75 | 55 | `project.architecture_walkthrough` ≥30 | P T F AP M |  |
| `project.incident_debugging_story` | T2 | 75 | 75 | 55 | `project.architecture_walkthrough` ≥30 | P T F AP M |  |

#### Group `pdd.engineering` — Practical engineering, debugging, performance

| Skill key | Tier | Imp | Target | Floor | Prerequisites (min score) | Evidence | Pattern |
|---|---|---:|---:|---:|---|---|---|
| `engineering.debugging` | T2 | 75 | 75 | 55 | — | P T F AP M |  |
| `engineering.performance_profiling` | T3 | 50 | 65 | — | `db.query_optimization` ≥45 | P T F AP M |  |
| `engineering.api_engineering` | T3 | 50 | 65 | — | `network.rest_semantics` ≥45 | P T F AP M |  |
| `engineering.tooling` | T4 | 20 | 50 | — | — | P T F AP M |  |
| `engineering.caching_practice` | T4 | 20 | 50 | — | `sd.caching` ≥45 | P T F AP M |  |

#### Group `pdd.testing` — Engineering testing

| Skill key | Tier | Imp | Target | Floor | Prerequisites (min score) | Evidence | Pattern |
|---|---|---:|---:|---:|---|---|---|
| `testing.unit_integration` | T3 | 50 | 65 | — | — | P T F AP M |  |
| `testing.test_design` | T3 | 50 | 65 | — | `testing.unit_integration` ≥45 | P T F AP M |  |

## 5. Coverage notes (what is deliberately included or excluded)

- **Included because the declared loop needs them:**
  - `lld.machine_coding` (T1);
  - `project.*` deep-dive skills;
  - `os.concurrency_practical` (thread pools, producer-consumer, asyncio, GIL);
  - `design_ds.core` (LRU-style questions);
  - `dsa.pattern_recognition` (T1) as a cross-pattern meta-skill;
  - SD execution skills (`sd.deep_dive_bottlenecks`, `sd.tradeoff_articulation`, `sd.time_boxing`).
- **Optional (T4), never blocking readiness:** MST, interval/state-machine DP, tree DP, bit manipulation, number theory, OS scheduling, distributed coordination, iterators/generators, tooling, caching practice.
- **Excluded from `seed-v1`:**
  - segment/Fenwick trees, Bellman-Ford, string matching (KMP/Z), consensus algorithm internals;
  - Kubernetes, frontend/CSS skills (the profile is backend-leaning full-stack, and the frontend is not an interview round in the declared loop).

  Adding one requires a `DECISION_LOG.md` entry.
- **Topics** (e.g. `exceptions` under `python.core_syntax`) are optional content tags, not skills. `seed-v1` populates them only where useful; problem selection uses problem→skill mappings.

## 7. Communication family (D-087, `seed-v3`)

Communication is its own **optional** skill family. Counts after `seed-v3`: 27 groups, 161 skills, **123 required (unchanged)**, 38 T4.

- **28 skills in 5 groups**, keys `comm.*`: `comm.spoken_foundation` (sentence_formation, question_formation, tense_consistency, articles_prepositions), `comm.fluency` (think_in_english, speak_30s, speak_1m, speak_2m, word_recovery, filler_reduction, delivery_confidence), `comm.workplace` (status_update, clarification_request, help_and_blockers, feedback_and_disagreement, senior_engineer_comms, meeting_participation), `comm.technical_explanation` (explain_code, explain_bug_root_cause, explain_decisions_tradeoffs, explain_query_optimization, explain_api_change, explain_architecture, explain_simply), `comm.writing` (chat_message, ticket_comment, email, tech_doc_incident).
- **All T4 (optional)**, so none counts in the 123-skill calibration denominator, in any component score or in G0/G1/G3. No baseline battery item covers them; their state comes from practice evidence only.
- **Component `coding`** is only a data slot (a skill needs one and the component enum is unchanged). It must never leak into technical readiness or track accounting: G8, track minutes, the stop list, the Prepare pages and every UI label treat `comm.*` as Communication (`is_optional_communication_skill`, `presentation/communication.ts`).
- **Prerequisites stay inside the family** (speak_1m needs speak_30s, explain_architecture needs explain_decisions_tradeoffs, ...). No required skill depends on a `comm.*` skill and technical weakness never blocks communication.
- **Interview communication reuses existing skills, no duplicates:** `communication.structured_answers` (STAR), `communication.followup_handling`, `execution.clarification`, `execution.think_aloud`, `behavioral.*`, `sd.execution.*`, `dsa.complexity_analysis`. The Communication Readiness area "Interview communication" aggregates them. `communication.*` stays required and behavioral.
- Roadmap: one optional milestone `COMM-1` on the `dsa_coding` track (no new track, no minute change; optional skills never block a milestone exit).
