#!/bin/sh
# Cross-container backup visibility check (D-077). Run after `make backup` against the RUNNING stack:
#   1. the backup container has LATEST and the file it names,
#   2. the backend container sees the same LATEST and file through its read-only /backups mount,
#   3. GET /api/v1/system/backup-status reports that file without a warning.
# Reads only; never writes into ./backups.
set -eu
COMPOSE=${COMPOSE:-docker compose}

fail() { echo "BACKUP STATUS CHECK FAILED: $*" >&2; exit 1; }

for service in backup backend; do
  $COMPOSE ps --status running --services | grep -qx "$service" || fail "service '$service' is not running (make dev)"
done

latest=$($COMPOSE exec -T backup cat /backups/LATEST) || fail "backup container has no /backups/LATEST (run make backup)"
file=$(echo "$latest" | cut -d' ' -f2)
$COMPOSE exec -T backup test -s "/backups/$file" || fail "backup container: /backups/$file is missing or empty"
echo "backup container : LATEST = $latest (file present)"

backend_latest=$($COMPOSE exec -T backend cat /backups/LATEST 2>/dev/null) \
  || fail "backend container cannot read /backups/LATEST: recreate it with 'docker compose up -d' (D-077)"
[ "$backend_latest" = "$latest" ] || fail "backend sees LATEST '$backend_latest', backup container sees '$latest'"
$COMPOSE exec -T backend test -s "/backups/$file" || fail "backend container: /backups/$file is missing"
if $COMPOSE exec -T backend test -w /backups; then fail "backend /backups is writable; it must be read-only"; fi
echo "backend container: same LATEST, file present, mount read-only"

$COMPOSE exec -T backend python - "$file" <<'EOF' || fail "backup-status endpoint does not report the latest backup"
import json, sys, urllib.request
data = json.load(urllib.request.urlopen("http://127.0.0.1:8000/api/v1/system/backup-status", timeout=5))["data"]
print("endpoint         :", json.dumps(data))
sys.exit(0 if data["available"] and data["latest_file"] == sys.argv[1] and not data["warning"] else 1)
EOF
echo "BACKUP STATUS OK: $file"
