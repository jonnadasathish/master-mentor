# Master Mentor — Evidence Model

## Purpose

Evidence answers:

> What can the candidate actually demonstrate?

Self-reported confidence is never sufficient to mark a skill as mastered.

## Evidence hierarchy

| Source | Base Strength |
|---|---:|
| Self assessment | 5 |
| Recall quiz | 10 |
| Easy practice | 15 |
| Medium practice | 25 |
| Hard practice | 35 |
| Timed exercise | 35 |
| Real project | 45 |
| Production-like task | 50 |
| Mock interview | 40 |

Base strength is not itself the skill score.

## Evidence record

```text
id
developer_id
skill_id
source_type
source_id
raw_score
difficulty
success
time_seconds
hints_used
confidence
observed_at
metadata_json
```

## Evidence quality modifiers

- no hint: 1.00
- one hint: 0.90
- multiple hints: 0.75
- copied/reproduced solution: 0.25
- timed completion: 1.10
- repeated independent success: up to 1.15
- very old evidence: decay modifier

## Problem evidence

For DSA, capture:

- result: solved/partial/failed
- first-attempt result
- time
- hints
- mistake type
- explanation score
- complexity score
- revision outcome

## Skill score

A deterministic weighted estimate:

1. Group evidence by skill.
2. Apply base strength.
3. Apply success/result multiplier.
4. Apply difficulty modifier.
5. Apply recency decay.
6. Compute weighted mean.
7. Cap to 0–100.
8. Compute confidence separately.

Suggested result multipliers:

- Pass: 1.00
- Partial: 0.60
- Fail: 0.00

Suggested difficulty multipliers:

- Easy: 0.80
- Medium: 1.00
- Hard: 1.20

## Confidence

Confidence is driven by:

- evidence count;
- evidence diversity;
- evidence recency;
- difficulty coverage.

Suggested bands:

- Low: <5 meaningful observations
- Medium: 5–11
- High: >=12

Confidence must not be confused with skill score.

## Skill status

- Unknown: insufficient evidence
- Weak: score < 50 with sufficient evidence
- Developing: 50–64
- Working: 65–74
- Strong: 75–84
- Interview Ready: 85–100

These are internal labels and can be tuned after real usage.
