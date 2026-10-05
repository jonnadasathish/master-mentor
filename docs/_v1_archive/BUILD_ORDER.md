# Master Mentor — Build Order

Use this exact order unless there is a strong technical reason not to.

1. Read `CLAUDE.md`, `PRD.md`, `PROJECT_CONTEXT.md`.
2. Build FastAPI + MySQL + Alembic foundation.
3. Build Vue foundation and authenticated shell.
4. Implement canonical skill graph and seed data.
5. Implement DSA problem/attempt tracking.
6. Implement evidence and skill-state calculation.
7. Implement deterministic gap engine.
8. Implement revision engine.
9. Implement daily mentor/mission engine.
10. Build Today page around the mentor output.
11. Add dashboard and weekly review.
12. Add CS, system design, practical engineering and behavioral tracking.
13. Add mocks.
14. Add readiness gates.
15. Add backup/export/import.
16. Perform deterministic replay test: same state + ruleset must produce same outputs.

## Claude execution rule

Before each major step, state:
- objective;
- files likely to change;
- database changes;
- tests required;
- acceptance criteria.

After completion, update `IMPLEMENTATION_PLAN.md`.
