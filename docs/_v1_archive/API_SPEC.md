# Master Mentor — API Specification

Base path: `/api/v1`

## Authentication

### POST `/auth/login`
Request:
```json
{"username":"...", "password":"..."}
```

Response:
```json
{"authenticated":true}
```

### POST `/auth/logout`

### GET `/auth/me`

---

## Goal

### GET `/goals/active`
Returns active goal.

### POST `/goals`
Creates a goal.

### PATCH `/goals/{id}`

---

## Skills

### GET `/skills`
Filters:
- category
- parent_id

### GET `/skills/{skill_id}`

### GET `/skills/{skill_id}/state`

---

## Problems

### GET `/problems`
Filters:
- difficulty
- skill_id

### POST `/problems/{problem_id}/attempts`

Example:
```json
{
  "result":"solved",
  "time_seconds":1320,
  "hints_used":0,
  "mistake_type":null,
  "confidence":4,
  "explanation_score":8,
  "complexity_score":9,
  "notes":"..."
}
```

---

## Revisions

### GET `/revisions/due`

### GET `/revisions/overdue`

### POST `/revisions/{id}/complete`

```json
{"outcome":"pass"}
```

---

## Gaps

### GET `/gaps`
Filters:
- status
- category
- min_priority

### GET `/gaps/top`

---

## Daily Plan

### GET `/daily-plan/today`

### POST `/daily-plan/generate`

### POST `/daily-plan/items/{id}/complete`

### POST `/daily-plan/items/{id}/skip`

### POST `/daily-plan/items/{id}/defer`

---

## Mocks

### GET `/mocks`

### POST `/mocks`

### POST `/mocks/{id}/scores`

---

## Weekly Review

### GET `/weekly-review/current`

### POST `/weekly-review/{id}/complete`

---

## Dashboard

### GET `/dashboard`

Response should contain:

- readiness
- readiness components
- top gaps
- due revisions
- today's plan
- target countdown
- streak
- current roadmap phase

---

## Export

### GET `/export/json`

### GET `/export/csv`

## Import

### POST `/import/preview`

### POST `/import/commit`

## Backup status

### GET `/system/backup-status`

All API errors should use a consistent structure:

```json
{
  "error": {
    "code":"VALIDATION_ERROR",
    "message":"...",
    "details":{}
  }
}
```
