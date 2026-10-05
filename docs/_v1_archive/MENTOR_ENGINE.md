# Master Mentor — Mentor, Revision and Daily Plan Engine

## 1. Revision intervals

Base intervals:

`1, 3, 7, 14, 30, 60 days`

Outcome rules:

| Outcome | Action |
|---|---|
| Pass | advance one interval |
| Partial | repeat current interval |
| Fail | reset to 1 day |
| Missed/No-show | treat as Fail |

Repeated failures should also create a gap reason.

## 2. Daily time budget

Default: 90 minutes.

Configurable by user.

Maximum generated tasks: 6.

## 3. Task classes

| Task | Base Priority |
|---|---:|
| Overdue revision | 100 |
| Critical gap | 90 |
| High gap | 80 |
| Due revision | 70 |
| Roadmap required topic | 60 |
| Maintenance | 40 |
| Exploration | 20 |

## 4. Allocation

Default for 90 minutes:

- 60% highest-priority remediation/revision
- 25% secondary gap
- 15% maintenance

If overdue revisions consume the entire budget, generate overdue revisions first and mark:

`BACKLOG_OVER_BUDGET`.

## 5. Tie breakers

1. Higher priority
2. Older due date
3. Lower skill score
4. Higher role importance
5. Older last-practiced date
6. Stable entity ID

## 6. Reason explanation

Every mission must expose:

- selected skill
- current score
- target score
- priority
- evidence that caused selection
- reason codes
- expected duration
- expected outcome

Example:

> Graph BFS selected because current score is 42/80, three of the last five graph attempts failed pattern identification, and the skill is high importance for the target profile.

## 7. Mission progression

For a gap:

### Stage 1 — Recall
Explain concept without notes.

### Stage 2 — Guided practice
Complete a constrained exercise.

### Stage 3 — Independent practice
Solve without hints.

### Stage 4 — Timed practice
Solve under time pressure.

### Stage 5 — Interview simulation
Think aloud, code, test and defend trade-offs.

## 8. Weekly review

Every week calculate:

- active days
- planned minutes
- completed minutes
- plan completion %
- revision completion %
- top 5 gaps
- gap changes
- mock scores
- readiness change
- overdue backlog
- strongest improvement
- biggest regression

Generate next-week focus from the ranked gaps.

## 9. Anti-overload rule

If the user has many gaps, do not create tasks for all of them.

Daily plan must focus on the highest-impact limited set.

The mentor can say:

> Do not start a new topic today. Fix this weak area first.
