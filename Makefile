# Master Mentor — developer commands. All tooling runs inside the compose containers, so the host
# only needs Docker (and make; without make use ./scripts/make-in-docker.sh <target>).

COMPOSE      ?= docker compose
PROJECT      ?= master-mentor  # must match COMPOSE_PROJECT_NAME in .env
HOST_UID     ?= $(shell id -u)
HOST_GID     ?= $(shell id -g)
BACKEND_RUN  := $(COMPOSE) run --rm -T backend
BACKEND_NODB := $(COMPOSE) run --rm --no-deps -T backend
FRONTEND_RUN := $(COMPOSE) run --rm --no-deps -T frontend

.DEFAULT_GOAL := help
.PHONY: help env dev down db-up db-migrate backup backup-verify backup-status-check restore-live export dev-reset seed-validate seed seed-lock seed-status lint typecheck test check format frontend-deps logs

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-14s %s\n", $$1, $$2}'

env: ## Fail early if .env is missing
	@test -f .env || { echo "Missing .env: copy .env.example to .env and set the CHANGE_ME values"; exit 1; }

dev: env ## Build and start mysql + backend + frontend, wait until healthy, apply migrations, load the catalog
	$(COMPOSE) up -d --build --wait
	$(MAKE) db-migrate
	$(MAKE) seed
	@echo "Frontend: http://127.0.0.1:$${FRONTEND_HOST_PORT:-5173}   API: http://127.0.0.1:$${BACKEND_HOST_PORT:-8000}/api/v1/health"

down: ## Stop the stack (data volume is kept)
	$(COMPOSE) down

db-up: env ## Start MySQL and wait until healthy
	$(COMPOSE) up -d --wait mysql

db-migrate: db-up ## Apply Alembic migrations to the application database
	$(BACKEND_RUN) alembic upgrade head

backup: db-up ## Take a backup now into ./backups (also runs nightly in the backup service)
	$(COMPOSE) run --rm -T --entrypoint /scripts/backup-once.sh backup

backup-verify: db-up ## Backup now, restore it into a scratch DB and compare every table's row count
	$(COMPOSE) run --rm -T --entrypoint /scripts/backup-once.sh backup
	$(COMPOSE) run --rm -T -e MYSQL_ROOT_PASSWORD --entrypoint /bin/bash backup -c \
		'/scripts/restore-verify.sh /backups/$$(cut -d" " -f2 /backups/LATEST)'

backup-status-check: ## Check the running backup + backend containers share ./backups and the status endpoint sees LATEST
	COMPOSE="$(COMPOSE)" ./scripts/backup-status-check.sh

restore-live: db-up ## DESTRUCTIVE: replace the live DB with FILE=backups/x.sql.gz (needs CONFIRM=RESTORE-LIVE-DATABASE)
	@test -n "$(FILE)" || { echo "usage: make restore-live FILE=backups/<file>.sql.gz CONFIRM=RESTORE-LIVE-DATABASE"; exit 2; }
	$(COMPOSE) stop backend
	$(COMPOSE) run --rm -T -e MYSQL_ROOT_PASSWORD -e CONFIRM=$(CONFIRM) --entrypoint /scripts/restore-live.sh backup /backups/$(notdir $(FILE))
	$(COMPOSE) up -d --wait backend

export: db-up ## Write a full JSON export and a CSV zip of all preparation data into ./exports
	$(COMPOSE) run --rm -T --user $(HOST_UID):$(HOST_GID) -v $(CURDIR)/exports:/exports backend python -m app.cli.export all --out /exports

dev-reset: db-up ## DEV ONLY: back up, then delete all preparation data, keep the catalog (needs CONFIRM=RESET-PREP-DATA)
	$(MAKE) backup
	$(BACKEND_RUN) python -m app.cli.devtools reset-prep --confirm "$(CONFIRM)"

seed-validate: env ## Validate seed/*.yaml (no database writes); non-zero exit on any error
	$(BACKEND_NODB) python -m app.cli.catalog validate

seed: db-up ## Validate, then load the catalog idempotently (aborts before writes if invalid)
	$(BACKEND_RUN) python -m app.cli.catalog seed

seed-lock: env ## Freeze fingerprints for a NEW seed_version in seed/seed.lock.yaml (append-only)
	$(COMPOSE) run --rm --no-deps -T --user $(HOST_UID):$(HOST_GID) backend python -m app.cli.catalog lock

seed-status: db-up ## Show which catalog version is loaded
	$(BACKEND_RUN) python -m app.cli.catalog status

lint: env ## ruff (lint + format check) and eslint (zero warnings)
	$(BACKEND_NODB) sh -c "ruff check . && ruff format --check ."
	$(FRONTEND_RUN) npm run lint

typecheck: env ## mypy (strict for app.domain) and vue-tsc
	$(BACKEND_NODB) mypy
	$(FRONTEND_RUN) npm run typecheck

test: db-up ## pytest (unit, API, migrations on the *_test DB) and vitest
	$(BACKEND_RUN) pytest
	$(FRONTEND_RUN) npm test

check: lint typecheck test ## All quality gates (required before a slice is done)
	@echo "make check: all checks passed"

format: env ## Auto-format backend and frontend
	$(BACKEND_NODB) sh -c "ruff check --fix . && ruff format ."
	$(FRONTEND_RUN) npx eslint . --fix

frontend-deps: env ## Rebuild the frontend image and reset node_modules after package.json changes
	$(COMPOSE) rm -sf frontend
	-docker volume rm $(strip $(PROJECT))_frontend_node_modules
	$(COMPOSE) build frontend

logs: ## Follow service logs
	$(COMPOSE) logs -f
