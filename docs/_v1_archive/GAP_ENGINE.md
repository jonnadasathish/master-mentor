# Master Mentor — Deterministic Gap Engine

## Goal

Convert current evidence into a ranked list of what the candidate should improve next.

## Inputs

- developer goal
- target role
- seniority
- target date
- canonical skill graph
- current skill state
- prerequisites
- role importance
- recent practice
- mock weaknesses
- revision state

## Step 1 — Determine target score

Each skill has a required target score based on the target profile.

Example:

```text
Senior Backend Engineer

system_design = 80
db.indexing = 80
graph.bfs = 75
frontend.css = 30
```

## Step 2 — Raw gap

```text
raw_gap = max(target_score - current_score, 0)
```

If skill is Unknown, use an assessment priority rather than pretending the gap is known.

## Step 3 — Factors

### Role importance

0.0 to 1.0.

### Criticality

- critical prerequisite: 1.20
- required: 1.00
- useful: 0.75
- optional: 0.40

### Recency risk

| Days since practice | Modifier |
|---:|---:|
| 0–3 | 0.90 |
| 4–7 | 1.00 |
| 8–14 | 1.10 |
| 15–30 | 1.20 |
| >30 | 1.35 |

### Failure pressure

- repeated failures: up to 1.25
- repeated hints: up to 1.15
- mock weakness: +0.15 max

## Priority

```text
priority_raw =
    raw_gap
    * role_importance
    * criticality
    * recency_risk
    * failure_pressure
```

Normalize to 0–100.

## Gap classes

### Knowledge gap
Low conceptual/assessment performance.

### Practice gap
Concept score acceptable but task performance is weak.

### Retention gap
Previously strong skill has decayed after inactivity.

### Speed gap
Correct but slower than target.

### Pattern-recognition gap
Repeated failures despite knowing underlying concepts.

### Communication gap
Solution is correct but explanation/clarification is weak.

### Depth gap
Basic implementation works but advanced follow-up fails.

### Experience gap
The candidate understands the concept but has little practical evidence.

## Gap status

- Critical: priority >= 80
- High: 60–79
- Medium: 40–59
- Low: 20–39
- None: <20

## Dependency rule

If a gap has weak prerequisites, prioritize prerequisites before the downstream skill.

Example:

```text
system_design.consistency
requires:
  db.transactions
  network.basics
  distributed_systems.basics
```

If prerequisites are below their minimum level, add reason code:

`PREREQUISITE_BLOCKED`.

## Reason codes

- LOW_SCORE
- LARGE_RAW_GAP
- HIGH_ROLE_IMPORTANCE
- RETENTION_RISK
- REPEATED_FAILURE
- MOCK_WEAKNESS
- SPEED_GAP
- PATTERN_RECOGNITION
- PREREQUISITE_BLOCKED
- LOW_CONFIDENCE
- OVERDUE_REVISION

## Required output

```json
{
  "skill_id": "graph.bfs",
  "current_score": 42,
  "target_score": 80,
  "priority": 88,
  "status": "critical",
  "gap_type": "pattern_recognition",
  "confidence": "high",
  "reason_codes": [
    "LARGE_RAW_GAP",
    "REPEATED_FAILURE",
    "PATTERN_RECOGNITION"
  ]
}
```

## Important rule

The Gap Engine identifies the problem.

It does not decide the full lesson content.

Mission selection belongs to the Mentor/Mission Engine.
