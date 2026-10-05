# Master Mentor — Claude Build Kit

Master Mentor is a private, single-user web application for tracking preparation for product-company software engineering interviews.

## Stack

- Frontend: Vue 3 + Vite + Pinia
- Backend: FastAPI + Python
- Database: MySQL 8+
- Styling: Vuetify 3 or a clean utility/CSS system
- Migrations: Alembic
- Containerization: Docker Compose
- Authentication: single-user local authentication
- AI/LLM: none in MVP
- External paid services: none required

## Core loop

Assess → Detect gaps → Plan → Practice → Record evidence → Revise → Mock → Recalculate readiness.

## Files

| File | Purpose |
|---|---|
| `PRD.md` | Product requirements and acceptance criteria |
| `PROJECT_CONTEXT.md` | Persistent product/engineering context for Claude |
| `CLAUDE.md` | Claude Code instructions and working rules |
| `AGENTS.md` | General AI-agent engineering rules |
| `ROADMAP.md` | Complete basic-to-advanced preparation curriculum |
| `SKILL_GRAPH.md` | Canonical interview skill graph |
| `EVIDENCE_MODEL.md` | Evidence, scoring and confidence rules |
| `GAP_ENGINE.md` | Deterministic gap detection and prioritization |
| `MENTOR_ENGINE.md` | Daily plan, mission and revision logic |
| `DATA_MODEL.md` | Database entities and relationships |
| `API_SPEC.md` | REST API contract |
| `UI_SPEC.md` | Pages, components and UX behavior |
| `IMPLEMENTATION_PLAN.md` | Incremental build plan for Claude |
| `TRACKING_SCHEMA.md` | Markdown-based human progress tracker |

## How to use with Claude Code

1. Copy the project files into the repository root.
2. Read `CLAUDE.md` first.
3. Treat `PRD.md` and `PROJECT_CONTEXT.md` as source-of-truth.
4. Build one vertical slice at a time.
5. After every feature, update `IMPLEMENTATION_PLAN.md` and relevant tracking state.
6. Do not introduce LLM APIs into the deterministic mentor engine.
