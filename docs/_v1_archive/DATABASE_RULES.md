# Master Mentor — Database and State Rules

## Indexing

At minimum index:

- all foreign keys;
- `problem_attempts(user_id, attempted_at)`;
- `evidence(user_id, skill_id, observed_at)`;
- `revisions(user_id, due_at, status)`;
- `gap_states(user_id, priority, status)`;
- `daily_plans(user_id, plan_date)`;
- `mocks(user_id, occurred_at)`.

## State rebuild

Derived state must be rebuildable from raw records.

At minimum the application must be able to recalculate:
- skill states
- gaps
- readiness
- due revision status
- current daily plan

from authoritative records.

## Idempotency

Mentor generation endpoints should be idempotent for the same:
- user
- date
- ruleset version
- current state hash

## Soft deletes

Use soft deletion only where historical references require it.
Never soft-delete an evidence record simply because the associated skill/problem is retired.

## Auditability

State-changing actions should be traceable through audit logs.

## Backup

Nightly compressed MySQL dump.
Retention: 14 days.
A restore test must be performed before declaring the backup system production-ready.
