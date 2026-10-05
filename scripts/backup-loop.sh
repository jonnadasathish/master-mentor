#!/bin/bash
# Nightly backup loop for the `backup` compose service: one backup at BACKUP_HOUR_UTC every day.
# It also takes a backup at start if none exists yet, so a fresh stack is protected immediately.
set -uo pipefail
HOUR=${BACKUP_HOUR_UTC:-21}   # 21:00 UTC = 02:30 IST
[ -f "${BACKUP_DIR:-/backups}/LATEST" ] || /scripts/backup-once.sh || echo "initial backup failed" >&2
while true; do
  now=$(date -u +%s)
  next=$(date -u -d "today ${HOUR}:00" +%s)
  [ "$next" -le "$now" ] && next=$(date -u -d "tomorrow ${HOUR}:00" +%s)
  echo "next backup at $(date -u -d "@$next" '+%Y-%m-%dT%H:%MZ')"
  sleep $((next - now))
  /scripts/backup-once.sh || echo "backup failed at $(date -u)" >&2
done
