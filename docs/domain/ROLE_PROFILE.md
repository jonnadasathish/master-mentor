# Master Mentor — Role Profile (Spec v2)

**Profile key:** `backend_fullstack_sde2` · **Seed version:** `seed-v1` · **Machine-readable source:** [`seed/role_profiles/backend_fullstack_sde2.yaml`](../../seed/role_profiles/backend_fullstack_sde2.yaml)

If this document and the YAML disagree, **the YAML wins**, and the seed validator plus this document must be fixed in the same change.

## 1. What this profile is

This profile is the internal benchmark Master Mentor measures you against. It is **not** a claim that any company uses this loop, these weights, or these thresholds. It encodes a deliberately demanding bar ("maximum readiness for top product-company / FAANG-style SWE interviews") so that passing it means real interview strength, not a flattering number.

| Field | Value |
|---|---|
| Role | Software Engineer, Backend/Full-Stack |
| Seniority benchmark | Mid-level, SDE-2 style |
| Objective | Maximum readiness for top product-company / FAANG-style SWE interviews |
| Preparation time | 600 min/week (10 h); default weekday budgets Mon–Fri 90, Sat–Sun 75 |
| Interview language | Python |

Ownership split:
- **This document** owns *parameters*: rounds, components, weights, tiers, targets, floors, gate thresholds, and track minutes.
- **`READINESS_MODEL.md`** owns gate *logic*.
- **`SKILL_GRAPH.md` / `seed/skills.yaml`** own the *skills*.

## 2. Declared interview loop

| # | Round | Round type | Minutes | Components evidenced |
|---|---|---|---:|---|
| 1 | DSA / Coding 1 | `DSA` | 45 | `dsa`, `coding` |
| 2 | DSA / Coding 2 | `DSA` | 45 | `dsa`, `coding` |
| 3 | CS Fundamentals | `CS` | 30 | `cs` |
| 4 | LLD / OOD / Machine coding | `LLD` | 90 | `lld` |
| 5 | System Design | `SYSTEM_DESIGN` | 45 | `system_design` |
| 6 | Behavioral / Leadership | `BEHAVIORAL` | 30 | `behavioral` |
| 7 | Project / Technical Deep Dive | `PROJECT_DEEP_DIVE` | 30 | `project` |
| 8 | Final mixed simulation | — | 160 | gate **G9** (not a component) |

## 3. Readiness components

| Component | Name | Weight | Gate (G2 min) | Stretch (STRONG min) | Track | Required skills | Target mean* |
|---|---|---:|---:|---:|---|---:|---:|
| `dsa` | DSA | 25 | 72 | 80 | `dsa_coding` | 39 | 75.66 |
| `coding` | Coding & Execution | 10 | 70 | 78 | `dsa_coding` | 13 | 73.33 |
| `cs` | CS Fundamentals | 12 | 70 | 78 | `cs` | 23 | 74.71 |
| `lld` | LLD / OOD | 13 | 72 | 80 | `lld` | 6 | 77.00 |
| `system_design` | System Design | 18 | 72 | 80 | `system_design` | 21 | 75.91 |
| `behavioral` | Behavioral | 10 | 70 | 78 | `behavioral_project` | 12 | 75.00 |
| `project` | Project Deep Dive | 12 | 70 | 78 | `behavioral_project` | 9 | 73.40 |
| | **Total** | **100** | | | | **123** | |

\* Target mean = importance-weighted mean of the required skills' targets, as computed by the seed generator. **Invariant (seed validator):** every component's `gate ≤ target mean`. If all required skills are exactly at target with HIGH confidence, every G2 gate passes. Being at floor everywhere fails every gate.

Why these weights: two of the seven rounds are DSA, so DSA plus coding together get 35. System design is the largest single non-coding signal for SDE-2, so it gets 18. LLD and project deep dive are separate rounds in the declared loop, so each gets a component rather than being folded into "practical engineering".

## 4. Tiers (importance, target, floor)

| Tier | Label | Importance | Target | Floor | Required | Count |
|---|---|---:|---:|---:|---|---:|
| T1 | CRITICAL | 100 | 80 | 65 | yes | 35 |
| T2 | CORE | 75 | 75 | 55 | yes | 56 |
| T3 | SUPPORTING | 50 | 65 | — | yes | 32 |
| T4 | OPTIONAL | 20 | 50 | — | no | 10 |

Meaning of the targets in evidence terms (bands from `EVIDENCE_MODEL.md` §7):
- **T1 target 80:** an L5 (explain) skill with near-perfect quality, or L6 (transfer), with HIGH confidence.
- **T2 target 75:** solid L5.
- **T3 target 65:** solid L4 (timed).
- **T4 target 50:** L3 (independent).

Floors: T1 65 ≈ reliable L4. T2 55 ≈ reliable L3.

## 5. Critical skills (T1, 35)

These must each reach `effective_score ≥ 65` **and** `level ≥ L4` for gate G4. T1 skills are never PARKED.

| Component | Critical skills |
|---|---|
| `dsa` (11) | `dsa.complexity_analysis`, `hashing.lookup_frequency`, `two_pointers.core`, `sliding_window.core`, `binary_search.basic`, `recursion.fundamentals`, `trees.traversal`, `heap.top_k`, `graph.traversal`, `dp.fundamentals`, `dsa.pattern_recognition` |
| `coding` (2) | `execution.brute_force_to_optimal`, `execution.bug_free_coding` |
| `cs` (6) | `db.sql_querying`, `db.indexing`, `db.transactions_acid`, `os.processes_threads`, `os.synchronization`, `network.http` |
| `lld` (3) | `lld.requirements_entities`, `lld.class_design`, `lld.machine_coding` |
| `system_design` (8) | `sd.requirements_scoping`, `sd.high_level_decomposition`, `sd.data_modeling`, `sd.caching`, `sd.database_scaling`, `sd.queues_async`, `sd.deep_dive_bottlenecks`, `sd.tradeoff_articulation` |
| `behavioral` (3) | `behavioral.ownership`, `behavioral.impact`, `communication.structured_answers` |
| `project` (2) | `project.architecture_walkthrough`, `project.tradeoffs_decisions` |

## 6. Target score by major skill area

The full per-skill list (tier, importance, target, floor, prerequisites) is in [`SKILL_GRAPH.md`](SKILL_GRAPH.md). Summary by group:

| Group | T1 | T2 | T3 | T4 | Notes |
|---|---:|---:|---:|---:|---|
| Python (`lang.python`) | 0 | 2 | 3 | 1 | Fluency is measured through coding evidence |
| Interview execution (`coding.execution`) | 2 | 4 | 2 | 0 | Rubric dimensions of timed attempts and mocks |
| DSA (6 groups) | 11 | 21 | 7 | 5 | Optional: MST, interval/state-machine DP, tree DP, bits, number theory |
| DBMS | 3 | 4 | 1 | 0 | Replication/sharding live in `system_design` (one key per concept) |
| OS & concurrency | 2 | 1 | 2 | 1 | `os.concurrency_practical` covers asyncio/GIL/thread pools |
| Networking | 1 | 3 | 3 | 0 | LB/CDN live in `system_design` |
| OOP + security | 0 | 2 | 1 | 0 | Design patterns live in `lld` |
| LLD / OOD | 3 | 2 | 1 | 0 | Machine coding is T1 |
| System design (3 groups) | 8 | 8 | 5 | 1 | Execution skills (deep dive, trade-offs, time-boxing) are first-class |
| Behavioral + communication | 3 | 6 | 3 | 0 | |
| Project deep dive + engineering + testing | 2 | 3 | 4 | 2 | Engineering testing ≠ `execution.testing_dry_run` |

## 7. Required gates (parameters)

Gate logic lives in `READINESS_MODEL.md`. Parameters:

| Gate | Parameter values |
|---|---|
| G0 Measured | ≥ 70% of required skills per component assessed |
| G1 Foundation exit | every component score ≥ 45; every T1 skill level ≥ L3 |
| G2 Component thresholds | per §3 "Gate" column |
| G3 Coverage | ≥ 80% of required skills per component at confidence ≥ MEDIUM |
| G4 Critical skills | every T1: `effective_score ≥ 65` and `level ≥ L4` |
| G5 No critical gaps | zero gaps with status `CRITICAL` |
| G6 Mocks | last 60 days: ≥ 3 DSA rounds, ≥ 2 of each other round type, ≥ 1 non-SELF round per type; mean of last 6 rounds ≥ 70; latest per type ≥ 65; each of last 3 rounds ≥ 55 |
| G7 Revision health | no T1/T2 revision item overdue > 7 days; 30-day pass rate ≥ 70% over ≥ 10 reviews |
| G8 Recency | every component has qualifying evidence (L1+, outcome ≥ 60) in the last 21 days |
| G9 Final simulation | 3 most recent final simulations all pass (every round ≥ 70, mean ≥ 75), oldest within 30 days, SD and LLD each covered at least once, ≥ 2 of 3 non-SELF |
| STRONG | every component ≥ stretch; mean of last 6 mock rounds ≥ 80; INTERVIEW_READY sustained ≥ 14 days |

## 8. Tracks (weekly minutes)

| Track | Minutes/week | Components |
|---|---:|---|
| `dsa_coding` | 210 | dsa, coding |
| `cs` | 75 | cs |
| `lld` | 75 | lld |
| `system_design` | 90 | system_design |
| `behavioral_project` | 60 | behavioral, project |
| `mock` | 60 | (mock rounds) |
| weekly review + buffer | 30 | — |
| **Total** | **600** | |

These minutes are **soft floors**, not quotas. The mentor is gap-driven. A track gets a +10 candidate boost only when its component is failing its gate *and* it received < 50% of its minutes in the last 7 days (`MENTOR_ENGINE.md` §5).

## 9. Change process

1. Edit the YAML.
2. Bump `seed_version`.
3. Run `make seed-validate` (unique keys, acyclic graph, `gate ≤ target mean`, weights sum to 100, track minutes ≤ 600, weekday budgets = 600, …).
4. Run `make seed-lock` to freeze the new version's fingerprints, then `make seed`.
5. Add a `DECISION_LOG.md` entry.
6. Trigger a full mentor rebuild (once rebuild exists).

Historical mentor runs keep their old `seed_version`.
