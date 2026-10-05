# Master Mentor — UI Specification (Spec v2)

## 1. Principles

- The first screen answers: where am I, what to do today, why, what to stop.
- The UI **never calculates** a score, priority, gate or date. It renders server read models. The only client-side logic is the mission timer and form validation.
- Every recommendation shows its reason, and a "why" expander shows the exact metrics from the payload.
- Status is never shown by color alone: icons and text labels too (CRITICAL / HIGH / MEDIUM / LOW / BLOCKED / PARKED).
- Desktop-first (1280×720 minimum). Usable at 390 px width for logging on a phone.

## 2. Navigation (7 items, down from 13)

| Page | Purpose | API |
|---|---|---|
| **Today** (home) | state, blockers, plan, why, stop list, revision counts | `GET /today` |
| **Log** | capture any observation in one place; history; corrections | `POST /attempts`, `/assessments`, `/mocks`; `GET /observations` |
| **Skills** | component roll-up → group → skill detail; roadmap tab | `GET /skills`, `/skills/{key}`, `/roadmap` |
| **Revision** | queue by bucket, start a review, suspend/resume | `GET /revisions` |
| **Mocks** | log mocks/final simulations, round trends, repeated weaknesses | `POST /mocks`, `GET /observations?type=mock` |
| **Progress** | readiness history, gates table, weekly reviews + reflection, stop list history | `/readiness`, `/readiness/history`, `/weekly-reviews/*` |
| **Settings** | goal, weekday budgets, timezone, stories, projects, prompts, export | `/goals`, `/settings`, `/stories`, `/projects`, `/prompts`, `/export/json` |

Removed as separate pages: Dashboard (merged into Today and Progress), and the DSA, CS, System Design, Practical and Behavioral pages (now component filters on Skills).

## 3. Today page

```text
┌ DEVELOPING · limiting: System Design 58/72 · 34 weeks left · BUILD ─────────────┐
│ Blockers: G2 system_design 58 < 72 · G4 sd.caching L3 < L4 · G9 0/3 simulations │  [all gates ▸]
├ Mentor ─────────────────────────────────────────────────────────────────────────┤
│ "Do not start dp.fundamentals today. graph.traversal PATTERN_RECOGNITION is      │
│  HIGH (57): 3 of your last 4 unseen graph problems used the wrong approach." [why▸]│
├ Today's plan · 60 / 90 min ─────────────────────────────────────────────────────┤
│ 1 ⟳ Revision · PROBLEM F101 (reinforce) · 35m · overdue 5d          [Start]       │
│ 2 ◎ graph.traversal · Pattern drill · 25m · HIGH 57                 [Start] [why▸]│
│    expected: ≥ 4/5 correct → L3 evidence on dsa.pattern_recognition              │
├ Top gaps ───────────────────────────────────────────────────────────────────────┤
│ graph.traversal HIGH 57 PATTERN_RECOGNITION · dp.fundamentals CRITICAL 100 (held)│
├ Stop list ─────────────────── Revision: 2 overdue · 1 due · backlog 105 min ─────┤
└──────────────────────────────────────────────────────────────────────────────────┘
```

- In calibration mode the header becomes "Calibration · 34/123 skills measured · battery 3/12".
- **Start** opens the mission view: template instructions, problem links or statements, rubric card, and a timer (the time limit comes from the template).
- **Complete** opens the capture form prefilled from the plan item (mode, revision_item_key, timer value). Submitting shows the **effects panel**: skill before → after, gap priority change, revision created/rescheduled, readiness change. This is the feedback loop.
- **Skip** requires a reason. **Defer** moves the item to tomorrow.
- "No evidence" completion is a secondary action, labeled "Mark studied (no evidence)".

## 4. Log page

One form with a kind switch (Attempt / Assessment / Mock / Self-assessment sweep). The common attempt case needs ≤ 30 s:
- problem search;
- outcome;
- timer value;
- hints;
- "named the pattern before hints?";
- mistake chips;
- optional explanation/complexity/follow-up;
- self-rating.

The backdate field is visible. The history table offers a **Correct** action, which supersedes the row and never edits it.

## 5. Skills page

- Component cards showing score vs gate, assessed %, medium-confidence % and a blocker badge. Drill down to group, then a skill table (label, level, score/effective, confidence, gap status, type).
- **Skill detail:**
  - state + label;
  - gap with reasons and metrics;
  - prerequisites with ✓/✗ against `min_score`;
  - downstream skills;
  - evidence timeline (level, points, source, date);
  - revision items;
  - milestone;
  - recommended focus with template preview.
- **Roadmap tab:** tracks × milestones with completion, the current milestone highlighted, and battery progress.

## 6. Revision page

Tabs: Overdue · Due · Upcoming · Suspended · Graduated. Each row shows the item, skill, type, minutes, days overdue, lapses and `needs_reinforcement`. **Review** opens the same mission view (template `revision.*`). The banner shows backlog vs cap and any triage today.

## 7. Mocks page

Log a mock with rounds and per-skill outcomes, flagging weaknesses. Shows:
- the round score trend per round type;
- G6 status per type;
- repeated weaknesses (skills flagged in ≥ 2 rounds);
- final simulations with pass/fail and G9 progress.

## 8. Progress page

- readiness state timeline;
- weighted score line (labeled "display only");
- component lines vs gates;
- gates table G0–G9 with conditions;
- weekly reviews: metrics plus a reflection form;
- strongest improvement / biggest regression.

## 9. Responsiveness and accessibility

Usable at 1280×720, 1440×900, 1920×1080 and 390 px wide (Log + Today). Keyboard reachable, visible focus, labels on all inputs, text alternatives for status icons.
