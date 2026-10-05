# Master Mentor — Project Context

## Owner context

- Personal, single-user project.
- Primary goal: prepare for product-company SWE interviews.
- Developer has practical experience with PHP, JavaScript, Vue, SQL and FastAPI and wants to strengthen Python/backend, DSA, CS, system design and interview execution.
- Preferred engineering style: practical, strong foundations, no unnecessary complexity.
- Available build time for the website: about 10 hours/week.
- The website itself is a tool to support preparation, not the primary deliverable.
- Preparation content and skill definitions should remain usable even if UI changes.

## Product philosophy

Master Mentor should act like a strict mentor:

- identify the biggest gap;
- explain why it matters;
- prescribe the smallest high-impact practice;
- record what happened;
- reschedule revision;
- escalate or de-escalate the gap based on evidence.

The application must not simply report activity.

## Architecture principle

Use domain services rather than embedding mentor logic inside Vue components.

Preferred backend domains:

- `skills`
- `evidence`
- `assessments`
- `gaps`
- `revisions`
- `missions`
- `roadmap`
- `mocks`
- `readiness`
- `analytics`

## Determinism

The same:

- current database state,
- current date,
- target profile,
- mentor ruleset version

must produce the same:

- skill calculations,
- gap rankings,
- revision dates,
- daily mission ordering.

## Source of truth

- Raw activity records are authoritative.
- Derived skill state may be cached/rebuilt.
- State snapshots are for reproducibility, not as the source of truth.

## Development rule

Do not add an AI API to solve deterministic product logic.

LLM-assisted development is allowed through Claude Code, but the application itself must not depend on Claude, OpenAI, Gemini, Groq or similar services for the core mentor engine.

## UX principle

The first screen should answer:

> What should I do today?

The second question should be:

> Why?

The third should be:

> Am I improving?

## Preferred implementation sequence

Build vertical slices:

1. Auth + goal
2. Skill graph
3. DSA problem logging
4. Evidence calculation
5. Gap engine
6. Revision engine
7. Daily plan
8. Dashboard
9. Weekly review
10. Mocks
11. System design/CS/practical tracking
12. Backup/export

Do not build large UI shells before the domain logic exists.
