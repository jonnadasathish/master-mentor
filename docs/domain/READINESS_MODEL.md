# Master Mentor — Readiness Model (Spec v2, ruleset `v1`)

This document is the **single owner** of readiness logic. Gate *parameters* come from the role profile (`ROLE_PROFILE.md` §7, `gate_parameters` in the YAML). No other document may define readiness thresholds.

**Core rule:** the readiness **state** is determined only by gates. The weighted score is displayed for trend, but no average can produce, raise, or protect a state.

## 1. Contract

```python
calculate_component_scores(skill_states, profile) -> {component: ComponentScore}     # pure; used by the gap engine too
calculate_readiness(
    component_scores, skill_states, gap_report, mock_rounds, final_simulations,
    revision_health, previous_snapshots, profile, as_of_date,
) -> Readiness
```

There is no cycle. Component scores depend only on skill states. Gaps depend on component scores. Readiness depends on both.

## 2. Components and weights

| Component | Weight | G2 gate | Stretch |
|---|---:|---:|---:|
| `dsa` | 25 | 72 | 80 |
| `coding` | 10 | 70 | 78 |
| `cs` | 12 | 70 | 78 |
| `lld` | 13 | 72 | 80 |
| `system_design` | 18 | 72 | 80 |
| `behavioral` | 10 | 70 | 78 |
| `project` | 12 | 70 | 78 |

## 3. Scores and coverage

For component `c`, over its **required** skills R(c) (T1–T3; T4 excluded; PARKED skills included):

```text
component_score(c)   := round_half_up( Σ importance_s × eff_s / Σ importance_s )     eff_s = effective_score, unassessed → 0
assessed_pct(c)      := 100 × |{s ∈ R(c): confidence ≠ NONE}| // |R(c)|
medium_conf_pct(c)   := 100 × |{s ∈ R(c): confidence ∈ {MEDIUM, HIGH}}| // |R(c)|
weighted_score       := round_half_up( Σ weight_c × component_score(c) / 100 )        display only
limiting_component   := component with the largest (gate − component_score); ties by weight desc, then key
```

## 4. Gates

| Gate | Name | Passes when |
|---|---|---|
| **G0** | Measured | every component has `assessed_pct ≥ 70` |
| **G1** | Foundation exit | every `component_score ≥ 45` **and** every T1 skill has `level ≥ L3` |
| **G2** | Component thresholds | every `component_score ≥ gate(c)` |
| **G3** | Coverage | every component has `medium_conf_pct ≥ 80` |
| **G4** | Critical skills | every T1 skill has `effective_score ≥ floor (65)` **and** `level ≥ L4` |
| **G5** | No critical gaps | zero gaps with status `CRITICAL` (absolute scale, `GAP_ENGINE.md` §7) |
| **G6** | Mocks | over mock rounds in the last 60 days (§5): ≥ 3 `DSA` and ≥ 2 of each other round type; ≥ 1 non-SELF round per type; mean of the last 6 rounds ≥ 70; latest round per type ≥ 65; each of the last 3 rounds ≥ 55 |
| **G7** | Revision health | `overdue_t1_t2_over_7d = 0` (ACTIVE items only) **and** `reviews_30d ≥ 10` **and** `pass_rate_30d ≥ 70` (integer floor) (`REVISION_ENGINE.md` §9) |
| **G8** | Recency | every component has ≥ 1 scoring row with `outcome_points ≥ 60` in the last 21 days (rows on optional communication skills `comm.*` are ignored, see below) |
| **G9** | Final simulation | the 3 most recent **valid** final simulations (§6) all pass, the oldest is ≤ 30 days old, together they include `SYSTEM_DESIGN` and `LLD`, and ≥ 2 of them are non-SELF |

**Communication isolation (D-087).** The optional (T4) `comm.*` skills carry component `coding` only because every skill must have a component. Their practice never counts as recency for any technical component: G8 skips every `comm.*` row. Required communication skills (`communication.*`, STAR and follow-ups) are behavioral and unchanged. Communication Readiness is a separate, read-only view (`UI_SPEC.md`); it is not a component, has no weight or gate, and never feeds Overall Readiness. All other gates already read required skills only, so no further change was needed.

## 5. Mock round rules for G6

- Rounds are ordered by `occurred_at` desc, then id desc. Superseded mocks are excluded. Rounds inside final simulations count.
- `round_score` from a SELF mock is capped at 80 for every gate computation (same cap as evidence, `EVIDENCE_MODEL.md` §4).
- Round type → components: `DSA` → `dsa` + `coding`; every other type → its own component.

## 6. Final simulation

A mock is a **valid final simulation** when:
- `is_final_simulation = true`;
- it contains rounds of every type in `final_simulation.required_round_types` (`DSA`, `CS`, `BEHAVIORAL`, `PROJECT_DEEP_DIVE`) plus at least one of `SYSTEM_DESIGN`, `LLD`;
- all rounds fall within one local day.

It **passes** when every round score ≥ 70 and the mean of round scores ≥ 75 (SELF capped at 80).

The mentor schedules final simulations only when `simulation_eligible` (G0–G8 pass) and the day's budget is ≥ 160 minutes. A final simulation logged earlier still counts. G9 only requires recent passes.

## 7. Readiness states

| State | Condition | Meaning |
|---|---|---|
| `NOT_MEASURED` | G0 fails | Too little evidence to judge. Calibration first. |
| `FOUNDATION` | G0 passes, G1 fails | Some area is fundamentally weak (a component < 45 or a critical skill below independent level). |
| `DEVELOPING` | G0–G1 pass, any of G2–G9 fails | Building toward the interview bar. |
| `INTERVIEW_READY` | G0–G9 all pass | Meets the internal benchmark in every component, critical skills, mocks, revision health, recency, and final simulations. |
| `STRONG` | INTERVIEW_READY **and** every `component_score ≥ stretch(c)` **and** mean of the last 6 mock rounds ≥ 80 **and** state was INTERVIEW_READY or STRONG in every daily snapshot of the last 14 days | Margin above the bar, sustained. |

Flags:
- `simulation_eligible`: G0–G8 pass.
- `lapsed`: today's state < INTERVIEW_READY **and** some daily snapshot in the last 30 days was INTERVIEW_READY or STRONG.

These are internal benchmark states, not hiring predictions.

## 8. Blockers

A blocker is one failing **(gate, subject)** pair, not one failing gate. For example, G2 failing in two components produces two blockers. When several conditions fail for the same subject (G4: effective below floor **and** level below L4), they merge into one blocker that lists each condition.

**Message format:** component → `"{Component display name} {actual} < {required}"`; skill level → `"{skill} level L{actual} < L{required}"`; skill score → `"{skill} effective {actual} < {required}"`; merged conditions are joined with " / "; G6/G7/G9 → a short description, e.g. `"SYSTEM_DESIGN latest round 58 < 65"`, `"overdue T1/T2 > 7 days: 12"`, `"final simulation 2026-11-01 failed: SYSTEM_DESIGN 66 < 70"`.

```json
{"gate": "G2", "subject": "system_design", "actual": 42, "required": 72, "deficit": 30,
 "skills": ["sd.caching", "sd.database_scaling"], "message": "System Design 42 < 72"}
```

- `skills`: for component conditions, the 3 required skills of that component with the largest `importance × (target − effective)`; for skill conditions, the skill itself.
- `blockers`: failing conditions of the gates needed for the **next** state, in gate order; within a gate, component conditions before skill conditions, then deficit desc, then subject key asc. (NOT_MEASURED → G0; FOUNDATION → G1; DEVELOPING → G2–G9.)
- `all_failing`: every failing condition across G0–G9, for the full gate view.

## 9. No weighted average can hide a critical weakness

The guarantee is structural:
1. States are pure functions of gates. `weighted_score` appears in no gate.
2. G1 and G2 are per-component minimums.
3. G4 is a per-skill minimum on every T1 skill.
4. G5 is a per-skill priority ceiling.
5. G6 requires each round type separately, so strong DSA mocks cannot cover weak SD mocks.
6. Parked skills still count in component scores, so parking cannot hide a weakness.
7. Unassessed skills count as 0, so not measuring cannot hide a weakness.

**Worked example** (others at 75):

| dsa | coding | cs | lld | system_design | behavioral | project |
|---:|---:|---:|---:|---:|---:|---:|
| 90 | 75 | 85 | 75 | **42** | 90 | 75 |

- `weighted_score` = 22.50 + 7.50 + 10.20 + 9.75 + 7.56 + 9.00 + 9.00 = 75.51 → **76**.
- State: **FOUNDATION**, because G1 fails (system_design 42 < 45).
- Blockers: `G1 System Design 42 < 45 (deficit 3)`, plus any T1 skill below L3.
- `all_failing` additionally contains `G2 System Design 42 < 72` and every G4 SD critical-skill condition.
- `limiting_component = system_design`. The UI headline reads "FOUNDATION — 1 blocker · limiting: System Design 42/72", never "76% ready".

## 10. Output and persistence

```json
{
  "as_of_date": "2026-11-02", "run_id": 812, "ruleset_version": "v1",
  "state": "DEVELOPING", "simulation_eligible": false, "lapsed": false,
  "weighted_score": 61, "limiting_component": "system_design",
  "components": [{"key": "dsa", "score": 66, "gate": 72, "stretch": 80, "weight": 25,
                  "assessed_pct": 92, "medium_conf_pct": 64, "passes_gate": false}],
  "gates": [{"gate": "G0", "passed": true}, {"gate": "G2", "passed": false, "failing": 4}],
  "blockers": [], "all_failing": []
}
```

Each daily snapshot (`readiness_snapshots`, one row per local date, from that date's last mentor run) persists the full object. Trends, `STRONG` sustain, `lapsed`, and `SUBSTEP_DRILL` read snapshots.

## 11. Derived skill readiness labels (display)

These are skill labels (`EVIDENCE_MODEL.md` §10), not readiness states. A skill can be `INTERVIEW_GRADE` while readiness is `FOUNDATION`.
