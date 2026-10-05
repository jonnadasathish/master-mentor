#!/bin/bash
# Prove a backup can recreate the database: restore it into a scratch database and compare, for every table,
# the row count and CHECKSUM TABLE value with the live database. Run it right after taking the backup on a
# quiet system (the make target does), otherwise concurrent writes show up as DIFF.
# Requires MYSQL_ROOT_PASSWORD (scratch database creation). Never touches the live database.
set -euo pipefail
FILE=${1:?usage: restore-verify.sh <backup.sql.gz>}
SCRATCH="${MYSQL_DATABASE}_restorecheck"
ROOT=(mysql -h "${MYSQL_HOST:-mysql}" -u root -p"$MYSQL_ROOT_PASSWORD" --default-character-set=utf8mb4)
q() { "${ROOT[@]}" -N -e "$1" 2> >(grep -v "Using a password" >&2); }

gzip -t "$FILE"
q "DROP DATABASE IF EXISTS \`$SCRATCH\`; CREATE DATABASE \`$SCRATCH\` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;"
gunzip -c "$FILE" | "${ROOT[@]}" "$SCRATCH" 2> >(grep -v "Using a password" >&2)

# Expected counts come from the dump itself (INSERT statements are per table); compare with restored counts.
fail=0
for table in $(q "SELECT table_name FROM information_schema.tables WHERE table_schema='$SCRATCH' ORDER BY table_name"); do
  restored=$(q "SELECT COUNT(*) FROM \`$SCRATCH\`.\`$table\`")
  live=$(q "SELECT COUNT(*) FROM \`$MYSQL_DATABASE\`.\`$table\`" 2>/dev/null || echo "missing")
  sum_restored=$(q "CHECKSUM TABLE \`$SCRATCH\`.\`$table\`" | awk '{print $2}')
  sum_live=$(q "CHECKSUM TABLE \`$MYSQL_DATABASE\`.\`$table\`" | awk '{print $2}')
  status=OK; [ "$restored" = "$live" ] && [ "$sum_restored" = "$sum_live" ] || status=DIFF
  printf '%-28s rows=%-6s live_rows=%-6s checksum=%-11s %s\n' "$table" "$restored" "$live" "$sum_restored" "$status"
  [ "$status" = OK ] || fail=1
done
live_tables=$(q "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$MYSQL_DATABASE'")
restored_tables=$(q "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$SCRATCH'")
echo "tables: restored=$restored_tables live=$live_tables"
[ "$live_tables" = "$restored_tables" ] || fail=1
q "DROP DATABASE \`$SCRATCH\`;"
if [ "$fail" = 0 ]; then echo "RESTORE VERIFIED: $(basename "$FILE")"; else echo "RESTORE CHECK FAILED" >&2; exit 1; fi
