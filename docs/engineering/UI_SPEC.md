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

**First run and calibration (D-080).** Until the Starting Profile is completed every page leads to `/onboarding` (developer tools stay reachable); it is a focused wizard without the app navigation: welcome → you (name, years, roles) → target (role benchmark, date, time per day) → stack (chips + other) → your view (optional self-reported topic claims, labelled *Self-reported context — not yet verified*) → how calibration works (12 assessments, about 7 h in total spread across the normal schedule, why, what is captured, no pass/fail, honest failures are useful) → *Save my starting point* → "Your starting point is ready" (target, timeline, hours, **Start calibration**). Opened later (Settings → Starting profile) it edits in place. `/calibrate` is the hub: the phase card (Start / Continue calibration, View my roadmap when enough is measured, Baseline complete), progress (assessments, skills measured, time left, estimate, timeline), today's calibration work (the full mission cards), completed assessments, what calibration does. **Continue calibration** on Today is a router link to `/calibrate?start=1`; the hub then resumes the mission in progress or starts the first one not yet started, never one already finished, skipped or deferred (a mission whose assessment is already complete is shown under Completed). When nothing is pending today it says "You've finished today's calibration work" and names the next assessment; it never invents work. (D-081) On Today below the threshold the hierarchy is: progress and **Continue calibration**, the timeline, today's diagnostic items (compact, friendly names), what calibration means, readiness as a calm "Not measured yet", the week. **Hybrid Today (D-086, phase `ENOUGH_MEASURED`):** primary = *Today's learning* card (today's focus, why this is today's focus, estimated time, the session's steps, **Start today's learning** / **Continue today's learning**); secondary = calibration (the "enough evidence" card with *Continue calibration* and "These assessments will continue to sharpen your roadmap, but they don't block today's learning", progress, remaining calibration today); tertiary = other missions (revisions) under *Also today*. If today's plan has no learning mission, it offers *Add today's learning* (re-plan), or says the mission starts tomorrow when the server dropped it only for budget. Below the threshold Today stays calibration-only. Once the baseline is complete Today switches to the personalized mentor with a one-time "Baseline complete. Your personal roadmap is ready." banner.

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

## 9. Learning layer (D-083)

- **Prepare** areas: DSA, Python, CS Fundamentals, System Design, LLD / OOD, Practical engineering, Projects, Behavioral. The five scored areas keep their summary and add a **Learning path** (topics in teaching order, each skill with score / target, status and coverage, and its learning items on demand). Python, Practical engineering and Projects are curriculum pages (`/prepare/python|engineering|projects`) and say where their skills are scored.
- **Skill page** (`/skills/:key`): why the skill matters (tier, the bar, rounds that test it, what builds on it, its topic and coverage), the existing "why this needs work", the mentor's next action with **Start a learning session** (the steps are previewed; "Continue the session" when one is active; "Start with <prerequisite>" when the gap engine focuses a prerequisite), and tabs **Learn / Practice / Test / Revise**. Practice states its case: direct problems with their practice state, related problems with the reason ("via Hashing — uses this skill"), concept practice, or an honest "no practice in the library yet" with the nearest practised skill and Log practice. A coding skill without its own problem is never sent to an empty problem list.
- **Problem list** filtered by a skill without problems shows that same resolution instead of "No problems match.". **Problem page** adds the practice state, the paraphrased summary, pattern and complexity (collapsed), a hint ladder revealed one hint at a time (to be counted when logging) and common mistakes (collapsed).
- **Content page** (`/learn/:key`): type, topic, minutes, optional timer, difficulty, skills and what completing it records. Lessons read in order (what, why, when, how, mental model, internals, example, complexity, trade-offs, edge cases, mistakes, misconceptions, interview, explain it) and end with "I've studied this" (minutes). Concept checks: choose, write short answers then compare with the model answer and grade yourself, declare notes; after submitting every explanation is shown. Recall cards flip and are rated. Practice items show the task, an optional interview timer, a hint ladder and the reference (both recorded honestly), then the rubric and follow-ups to rate. Projects show the brief, milestones (each recorded with its rubric) and the defense. The result shows points, passed or "the mentor will bring this back", what it records, and what changed.
- **Learning session** (`/learn/session/:id`): step list (status, minutes, points), the current step (content runner, problem with the attempt form, or reflection), skip and stop; the summary shows the outcome and score before → after, with Back to Today, See the skill, Repeat.
- **Today**: a pending skill mission shows the steps of its session and **Start the session** (or Continue); "Do it my way" keeps the original timer-and-log flow.
- **Mocks**: **Rehearse a round** — one tab per loop round with the skills to probe first and up to five timed prompts.
- **Settings → Developer → Content coverage**: per-state counts for required skills, the library's counts per type, and the per-skill table with a state filter.
- Content text is rendered from a safe subset (paragraphs, lists, code, inline code, bold) with render functions; no HTML is interpreted.

## 10. Communication (D-087)

- **Where.** Prepare has a **Communication** page (curriculum pattern, like Python and Projects). Today stays the primary UX: a communication mission looks like any mission, labelled "Communication", and an "explain it aloud" step appears inside a technical session marked *optional*. There is no separate English dashboard.
- **Speaking runner.** Shows the prompt, the target duration and a privacy line before the controls: "Speech recognition is provided by your browser's speech service. Master Mentor does not store audio. Only the transcript text you choose to submit is saved." (no claim that processing is local). Start/Stop with a live clock and a live transcript; the learner reviews and may edit the transcript, then "Check my signals" (server-measured) and rates themselves against the key points; submit unlocks only after review. Unsupported browser or blocked microphone: "Speech practice isn't supported in this browser." plus a complete **Manual practice** flow, labelled weaker evidence. The result says "Speaking practice completed" with signals ("96 words in 82 seconds", "2 filler words", "Included 2 of 3 target phrases"), never a percentage or an "English score".
- **Communication Readiness** (Communication page and Progress): six areas, each with a status word and one honest sentence ("Developing: based on 5 measured speaking practices." / "Not measured yet." / "Self-reported only, not measured yet."). It never appears among the seven readiness components and has no overall number. **Recent speaking practice** lists counts only, each row labelled Measured or Manual.
- **Isolation in the UI.** `comm.*` skills never appear on the DSA/Coding Prepare pages, are labelled "Communication" (not "Coding & Execution") in missions and on the skill page, and sit in their own optional section of the starting-profile self-report.
- **Accessibility.** Modes are a labelled button group (`aria-pressed`), the timer is `role="timer"`, status text is `role="status"`, errors `role="alert"`, ratings are labelled radio groups, and every control works by keyboard.
