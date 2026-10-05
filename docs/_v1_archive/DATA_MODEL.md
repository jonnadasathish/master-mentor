# Master Mentor — Data Model

## Core entities

### users
- id
- username
- password_hash
- timezone
- created_at
- updated_at

### goals
- id
- user_id
- target_role
- seniority
- target_date
- weekly_minutes
- active
- created_at

### skills
- id
- skill_key
- name
- category
- parent_id
- description
- default_importance
- active

### skill_relationships
- id
- skill_id
- related_skill_id
- relationship_type
- weight

Supported relationship types:
- prerequisite
- enables
- related
- parent

### role_skill_requirements
- id
- role_key
- skill_id
- target_score
- importance
- required
- created_at

### problems
- id
- title
- source_url
- difficulty
- active

### problem_skills
- problem_id
- skill_id
- weight

### problem_attempts
- id
- user_id
- problem_id
- attempted_at
- result
- time_seconds
- hints_used
- mistake_type
- confidence
- explanation_score
- complexity_score
- notes

### evidence
- id
- user_id
- skill_id
- source_type
- source_id
- raw_score
- difficulty
- confidence
- observed_at
- metadata_json

### skill_states
- user_id
- skill_id
- score
- confidence
- evidence_count
- last_observed_at
- last_practiced_at
- calculated_at
- ruleset_version

### revisions
- id
- user_id
- source_type
- source_id
- interval_index
- due_at
- last_outcome
- status
- created_at
- updated_at

### gap_states
- id
- user_id
- skill_id
- current_score
- target_score
- priority
- status
- gap_type
- confidence
- reason_codes_json
- calculated_at
- ruleset_version

### missions
- id
- user_id
- skill_id
- mission_type
- title
- description
- estimated_minutes
- difficulty
- status
- reason_codes_json
- created_at
- completed_at

### daily_plans
- id
- user_id
- plan_date
- time_budget
- total_allocated_minutes
- generated_at
- ruleset_version

### daily_plan_items
- id
- plan_id
- mission_id
- position
- allocated_minutes
- status

### mocks
- id
- user_id
- mock_type
- occurred_at
- duration_minutes
- overall_score
- notes

### mock_scores
- id
- mock_id
- skill_id
- score
- notes

### behavioral_stories
- id
- user_id
- title
- competency
- situation
- task
- action
- result
- learning
- strength_score
- last_reviewed_at

### weekly_reviews
- id
- user_id
- week_start
- week_end
- metrics_json
- top_gaps_json
- wins_json
- next_focus_json
- reviewed_at

### state_snapshots
- id
- user_id
- snapshot_at
- schema_version
- ruleset_version
- state_json

### audit_logs
- id
- user_id
- entity_type
- entity_id
- action
- payload_json
- created_at

## Key relationship

```text
User
 ├── Goal
 ├── Attempts
 ├── Evidence
 ├── Skill States
 ├── Gap States
 ├── Revisions
 ├── Missions
 ├── Plans
 ├── Mocks
 ├── Stories
 └── Weekly Reviews
```

## Design rule

Never delete historical `problem_attempts`, `evidence`, `mock_scores`, or `audit_logs` for normal correction flows.
