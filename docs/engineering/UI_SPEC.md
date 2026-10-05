# Master Mentor — UI Specification (Spec v2, UI/UX V2)

Decision D-078. The UI is a presentation layer over the server read models. It never calculates a score, gap, priority, readiness state, revision date or mentor message (CLAUDE.md rule 4).

## 1. Principles

- Opening the app answers five questions at once: where am I, what should I do today, why, how long will it take, am I improving.
- The tone is a calm personal coach: whitespace, one accent colour, a small semantic palette, strong type hierarchy. Not an admin panel, not a debug console.
- Human language everywhere in the daily experience. Internal terms (gate ids `G0…G9`, ruleset and seed identifiers, database ids, reason codes, raw skill keys) appear only under Settings → Developer / System. Wording of server codes lives in `src/presentation/*`; it words what the server sent and never invents a number.
- Every semantic state shows an icon **and** a text label (Critical, High, Medium, Healthy, Ready, Revision due, Overdue, Blocked, Calibrating, Completed; plus Low and Parked). Colour is never the only signal.
- No fake data. Missing data is shown as an empty, calibrating or "not measured" state.
- Desktop 1280+ is the primary layout; tablet 768–1279 uses an icon rail; phones (390 px minimum) are recomposed (bottom bar, mission first), not shrunk.

## 2. Navigation

| Item | Route | Contents |
|---|---|---|
| **Today** | `/` | greeting and phase, calibration or readiness, mentor message, today's missions, biggest gaps, strengths, this week, revision glance |
| **Prepare** | `/prepare` | hub: five areas with score, active gap, next step |
| · DSA | `/prepare/dsa` (+ `/problems`, `/problems/:key`, `/attempts/:id`) | today's DSA missions, weak spots, recent attempts, reviews, progress by pattern; problem search/filter; focused solving |
| · CS Fundamentals, System Design, LLD / OOD, Behavioral | `/prepare/cs`, `/system-design`, `/lld`, `/behavioral` | area summary, next step, needs attention, all skills (collapsed) |
| **Revise** | `/revise` | tabs Due · Overdue · Upcoming · Completed · Paused; review cards |
| **Mocks** | `/mocks` | next recommended mock, scores per round type, mentor diagnosis, recent mocks, log a mock |
| **Progress** | `/progress` | readiness and trend, what is holding you back, growth by area, revision health, mock trend, weekly consistency; weekly review at `/review` |
| **Roadmap** | `/roadmap` | roadmap order beside personal priority; current / completed / up-next milestones per track |
| **Settings** | `/settings` | name, goal and daily time, stories/projects/prompts, backup status, export/import; **Developer / System** at `/settings/developer` (health, versions, catalog check at `/settings/developer/catalog`, reset procedure) |

**First run and calibration (D-080).** Until the Starting Profile is completed every page leads to `/onboarding` (developer tools stay reachable); it is a focused wizard without the app navigation: welcome → you (name, years, roles) → target (role benchmark, date, time per day) → stack (chips + other) → your view (optional self-reported topic claims, labelled *Self-reported context — not yet verified*) → how calibration works (12 assessments, about 7 h in total spread across the normal schedule, why, what is captured, no pass/fail, honest failures are useful) → *Save my starting point* → "Your starting point is ready" (target, timeline, hours, **Start calibration**). Opened later (Settings → Starting profile) it edits in place. `/calibrate` is the hub: the phase card (Start / Continue calibration, View my roadmap when enough is measured, Baseline complete), progress (assessments, skills measured, time left, estimate, timeline), today's calibration work (the full mission cards), completed assessments, what calibration does. **Continue calibration** on Today is a router link to `/calibrate?start=1`; the hub then resumes the mission in progress or starts the first one not yet started, never one already finished, skipped or deferred (a mission whose assessment is already complete is shown under Completed). When nothing is pending today it says "You've finished today's calibration work" and names the next assessment; it never invents work. (D-081) On Today during calibration the hierarchy is: progress and **Continue calibration**, the timeline, today's diagnostic items (compact, friendly names), what calibration means, readiness as a calm "Not measured yet", the week. Once the baseline is complete Today switches to the personalized mentor with a one-time "Baseline complete. Your personal roadmap is ready." banner.

**Roadmap** (`/roadmap`) opens on *Your roadmap*: phase and timeline, "Your plan changed" (only when the engine reports a change), focus now (score/target, kind of work, reason, next step with minutes, what it waits on), already strong (not re-taught), later, parked, not measured, and "Why is this my roadmap?" (target role, date, measured count, biggest gaps, blocked skills, revision, and per-skill numbers). *Planned order* keeps the milestone tracks. **Progress** shows *Your current state* (strong / developing / critical / unknown) and, for every topic the user made a claim about, a "You said" panel (dashed, "Self-reported · not verified") beside a "Measured" panel (solid). A "new to me" self-rating is labelled as such and not counted as measured by a task.

Global action: **Log practice** (`/log`). Also reachable, not in the nav: `/baseline` (calibration), `/skills/:key` (skill detail). Old addresses (`/skills`, `/revision`, `/log/problems`, `/status`, `/catalog`) redirect.

## 3. Today

Order on desktop: header → (skill map banner) → calibration hero or nothing → mentor message → today's missions → biggest gaps → strengths → "not today" list; right rail: readiness, this week, revision. On phones the order is header, mentor, missions, readiness, gaps, week.

- **Header:** "Good morning, {name}." (the default name "Owner" is omitted) and "Day {n} · {phase} · {w} weeks to your interview" (`GET /today/week`.`preparation_day`, `GET /today`.`phase`). Phase wording: Calibration, Building foundations, Consolidation, Interview sharpening.
- **Calibration** (baseline not complete): see "First run and calibration" above: progress and Continue calibration, timeline, compact diagnostic list, what calibration means; no mentor message or mission cards (those live on `/calibrate`). Once calibration is done but readiness is still NOT_MEASURED, the readiness card lists what still needs a first assessment.
- **After the baseline:** a one-time "Baseline complete. Your personal roadmap is ready." banner with links to the roadmap and the current state (dismissal stored in `localStorage`), then readiness, strengths, gaps and missions.
- **Readiness card:** score out of 100 and state wording, component bars with a tick at the level aimed for, the limiting area, a trend line when history exists. Never a diagnostic table.
- **Mentor message:** the backend `plan.message.text` unchanged except that skill / baseline keys become names and an empty "Label: ." clause is dropped. "Why am I seeing this?" lists the payload in plain words.
- **Missions** (at most six shown, "Show n more"): number, title, minutes, skill, **Why this matters** (server numbers + reason sentences), expected outcome, Start. States: not started, in progress (timer), completed (the card transforms and keeps what changed), skipped, deferred, blocked. Secondary actions under "Other options": mark studied (no evidence), do it tomorrow, skip with a reason.
- **Biggest gaps** (≤ 5 shown): name, score / target, bar, state, one-line reason; each links to the skill.
- **This week:** recorded practice time against the weekly target, time by area, practice days, revision completion.

## 4. Solving and logging

- A problem page shows the problem facts, the mentor's suggestion, and Start. Solving is focused: the clock and a scratch-notes box with a single "Finish & log result" action. Then "How did it go?" (result, time, hints, confidence, explanation, complexity, mistakes, notes). Saving shows "Attempt recorded." and the real skill changes from the server; nothing is shown before the engines have run.
- Log practice offers: a coding problem (goes to the problem list), something else (any assessment kind and skill, optgroups by area), self-rating, a mock. History lists are short with "Show all"; corrections append a new version.

## 5. Skill detail

Score / target, status, confidence, evidence count; "Why this needs work" (from the gap metrics and reason codes); **Next best action** with Start; prerequisites with ready / needs-work icons and the numbers; recent evidence as a timeline; scheduled reviews; what it unlocks.

## 6. States

- **Loading:** skeletons shaped like the content (Today, cards, lists); never a bare "Loading…".
- **Empty:** a friendly title, one sentence and an action (no mocks yet, nothing due, nothing critical, no attempts).
- **Error:** "Master Mentor can't reach the preparation engine right now." with Retry; code and HTTP status only under "Technical details".
- **Motion:** card hover, progress bars, page fade, completion pop. `prefers-reduced-motion` disables all of it.

## 7. Accessibility

Skip link, one `h1` per page and ordered headings, labelled controls, visible focus ring, `aria-current` on the current page, tablist semantics for tabs, status icons with text, contrast ≥ 4.5:1 for text. An axe-core audit (WCAG 2 A/AA + best practices) reports 0 violations on every page at 1440 px and 390 px.

## 8. Data loading

Server read models are cached once per session by Pinia (`src/stores/data.ts`): navigating between pages does not refetch; writes refresh only what is already loaded (`refreshDerivedData`); Today is revalidated after 10 minutes. Typical cold load of Today: 7 distinct requests, no duplicates; moving to Prepare, DSA, Progress and Revise adds only what each page newly needs.
