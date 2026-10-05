# Master Mentor — Product Requirements Document

## 1. Product

**Name:** Master Mentor

**Positioning:** A private personal interview-preparation operating system that continuously measures the candidate's preparation state and tells them the highest-value next action.

**Primary goal:** Maximize readiness for software engineering interviews at product-based companies.

**Users:** One user only.

**Target preparation:** SWE / backend / full-stack product-company interviews, with DSA, CS fundamentals, system design, practical engineering, behavioral and mock interviews.

## 2. Product principles

1. Practice over passive consumption.
2. Evidence over self-reported confidence.
3. One clear next action.
4. Revision begins from Day 1.
5. Deterministic recommendations.
6. Every recommendation must be explainable.
7. The system must be able to say "not ready".
8. Never optimize for feature count; optimize for interview readiness.

## 3. Goals

- Track all preparation activity in one place.
- Detect weak topics and failure patterns.
- Schedule deterministic revision.
- Generate a daily plan within a time budget.
- Measure readiness across DSA, CS, system design, coding, testing, behavioral and interview execution.
- Maintain a complete history of evidence and mentor decisions.
- Support JSON/CSV export and MySQL backup.
- Work without external paid services.

## 4. Non-goals

- Multi-user SaaS.
- Social/community features.
- LLM chat.
- Automatic company scraping.
- Automatic LeetCode scraping in MVP.
- Job application tracking.
- Resume builder.
- Native mobile app.
- Hiring/outcome guarantees.

## 5. Core requirements

### Dashboard

| ID | Requirement | Priority |
|---|---|---|
| FR-1 | Show current readiness score and individual component scores. | Must |
| FR-2 | Show today's prioritized missions. | Must |
| FR-3 | Show critical/high gaps. | Must |
| FR-4 | Show due and overdue revisions. | Must |
| FR-5 | Show target date, current phase, and preparation streak. | Should |

### DSA

| ID | Requirement | Priority |
|---|---|---|
| FR-6 | Track DSA patterns and subskills. | Must |
| FR-7 | Log problem attempts with time, result, hints, mistakes, confidence and notes. | Must |
| FR-8 | Assign each problem to one or more patterns. | Must |
| FR-9 | Calculate pattern mastery. | Must |
| FR-10 | Detect failure patterns. | Must |

### Revision

| ID | Requirement | Priority |
|---|---|---|
| FR-11 | Automatically create revision schedules from qualifying events. | Must |
| FR-12 | Record Pass/Partial/Fail. | Must |
| FR-13 | Reschedule deterministically after each result. | Must |
| FR-14 | Prioritize overdue revisions. | Must |

### CS/System Design/Practical/Behavioral

| ID | Requirement | Priority |
|---|---|---|
| FR-15 | Track CS fundamentals as skills with evidence. | Must |
| FR-16 | Track system-design competencies and design exercises. | Must |
| FR-17 | Track practical-engineering competencies. | Must |
| FR-18 | Track behavioral stories and competencies. | Should |

### Mocks

| ID | Requirement | Priority |
|---|---|---|
| FR-19 | Record mock interviews and component scores. | Must |
| FR-20 | Calculate recent mock trend. | Must |
| FR-21 | Convert mock weaknesses into mentor priorities. | Must |

### Mentor

| ID | Requirement | Priority |
|---|---|---|
| FR-22 | Generate daily plan from current evidence and gaps. | Must |
| FR-23 | Explain every recommendation using reason codes and metrics. | Must |
| FR-24 | Keep daily plan inside configured time budget unless overdue backlog exceeds budget. | Must |
| FR-25 | Allow complete/skip/defer while preserving source evidence. | Must |

### State and safety

| ID | Requirement | Priority |
|---|---|---|
| FR-26 | Maintain one canonical current state. | Must |
| FR-27 | Version schema and mentor rules. | Must |
| FR-28 | Export complete data as JSON and CSV. | Must |
| FR-29 | Run nightly local backups. | Must |

## 6. Readiness model

Recommended initial dimensions:

- DSA — 30%
- Coding/interview execution — 15%
- CS fundamentals — 15%
- System design — 20%
- Practical engineering/testing — 10%
- Behavioral/communication — 10%

Readiness must be supplemented by gates. A high weighted score cannot hide a critical weakness.

Suggested gate thresholds:

- DSA >= 75
- CS >= 65
- System design >= 70
- Coding/execution >= 70
- Behavioral/communication >= 70
- Recent mock average >= 70
- Critical gaps = 0

These are Master Mentor internal thresholds, not claims about any company's hiring bar.

## 7. Acceptance principle

The product is MVP-complete when the user can:

1. Set a target date.
2. Work through the roadmap.
3. Log problems and other practice.
4. Automatically receive revisions.
5. See skill scores and gaps.
6. Receive an explainable daily plan.
7. Complete weekly reviews.
8. Conduct mock interviews.
9. See readiness change based on evidence.
10. Export and restore the full state.
