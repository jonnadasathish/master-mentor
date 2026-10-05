# AI Agent Engineering Rules

## Product source of truth

`PRD.md` > `PROJECT_CONTEXT.md` > domain-specific markdown > implementation.

When code conflicts with the documented rules, stop and reconcile the difference.

## Never do

- Do not add login providers.
- Do not add multi-user functionality.
- Do not add an LLM API.
- Do not scrape external websites in MVP.
- Do not invent interview requirements as facts about specific companies.
- Do not change mentor formulas without a ruleset version.
- Do not delete historical evidence because a newer calculation exists.
- Do not mix database access into Vue components.
- Do not put business rules into route handlers when a service is appropriate.

## Required

- Tests for mentor math.
- Tests for revision scheduling.
- Tests for gap ranking.
- Tests for readiness gates.
- Migration for schema changes.
- Auditability for state-changing user actions.
- Explainability for mentor recommendations.

## Security

- Password hashes only; never store passwords.
- Use secure cookie/session configuration.
- Validate all API inputs.
- Avoid rendering arbitrary HTML.
- Protect destructive actions with explicit confirmation.
- Never expose secrets to the frontend bundle.

## Definition of done

A feature is done only when:
- implementation works;
- domain rules are tested;
- API behavior is tested where applicable;
- UI supports the primary flow;
- documentation/tracker is updated.
