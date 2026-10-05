#!/bin/bash
# One consistent, compressed MySQL backup of the application database (runs inside the `backup` service).
# Uses the app user (no root); --single-transaction gives a consistent InnoDB snapshot without locking.
set -euo pipefail
DIR=${BACKUP_DIR:-/backups}
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-14}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
FILE="$DIR/${MYSQL_DATABASE}-${STAMP}.sql.gz"
mkdir -p "$DIR"
mysqldump -h "${MYSQL_HOST:-mysql}" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" \
  --single-transaction --no-tablespaces --routines --triggers --hex-blob --set-gtid-purged=OFF \
  --default-character-set=utf8mb4 "$MYSQL_DATABASE" 2> >(grep -v "Using a password" >&2) \
  | gzip -9 > "$FILE.tmp"
gzip -t "$FILE.tmp"                       # refuse to publish a corrupt archive
mv "$FILE.tmp" "$FILE"
printf '%s %s\n' "$STAMP" "$(basename "$FILE")" > "$DIR/LATEST"
find "$DIR" -maxdepth 1 -name "${MYSQL_DATABASE}-*.sql.gz" -mtime +"$RETENTION_DAYS" -print -delete
echo "backup written: $FILE ($(du -h "$FILE" | cut -f1))"
