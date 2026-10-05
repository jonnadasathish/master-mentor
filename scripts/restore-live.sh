#!/bin/bash
# DESTRUCTIVE: replace the live application database with a backup. Takes a safety backup first.
# Only runs with CONFIRM=RESTORE-LIVE-DATABASE. Stop the backend while restoring (make target does this).
set -euo pipefail
FILE=${1:?usage: restore-live.sh <backup.sql.gz>}
[ "${CONFIRM:-}" = "RESTORE-LIVE-DATABASE" ] || { echo "Refusing: set CONFIRM=RESTORE-LIVE-DATABASE" >&2; exit 2; }
gzip -t "$FILE"
/scripts/backup-once.sh   # safety copy of the current state
ROOT=(mysql -h "${MYSQL_HOST:-mysql}" -u root -p"$MYSQL_ROOT_PASSWORD" --default-character-set=utf8mb4)
"${ROOT[@]}" -e "DROP DATABASE \`$MYSQL_DATABASE\`; CREATE DATABASE \`$MYSQL_DATABASE\` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci; GRANT ALL PRIVILEGES ON \`$MYSQL_DATABASE\`.* TO '$MYSQL_USER'@'%';" 2> >(grep -v "Using a password" >&2)
gunzip -c "$FILE" | "${ROOT[@]}" "$MYSQL_DATABASE" 2> >(grep -v "Using a password" >&2)
echo "live database restored from $(basename "$FILE")"
