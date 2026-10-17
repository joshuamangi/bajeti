#!/usr/bin/env bash
# Check that the newest Bajeti backup is recent and restorable. Never touches the live database.
#
#   backup-verify.sh [backup-file]
#
# Exits non-zero if there is no backup, the newest one is older than MAX_AGE_HOURS (default 26),
# it is empty, fails PRAGMA integrity_check, or the users table cannot be read.
set -Eeuo pipefail

BACKUP_DIR="${BACKUP_DIR:-$HOME/backups/db_backups}"
MAX_AGE_HOURS="${MAX_AGE_HOURS:-26}"

die() { echo "VERIFY FAILED: $*" >&2; exit 1; }

file="${1:-}"
if [ -z "$file" ]; then
  file="$(find "$BACKUP_DIR" -maxdepth 1 -type f -name 'db_backup_*.db' | sort | tail -n 1)"
fi
[ -n "$file" ] && [ -f "$file" ] || die "no backup found in $BACKUP_DIR"
[ -s "$file" ] || die "$file is empty"

now="$(date +%s)"
if mtime="$(stat -c %Y "$file" 2>/dev/null)"; then :; else mtime="$(stat -f %m "$file")"; fi
age_h=$(( (now - mtime) / 3600 ))
echo "newest backup: $(basename "$file"), ${age_h}h old"
[ "$age_h" -le "$MAX_AGE_HOURS" ] || die "newest backup is ${age_h}h old (limit ${MAX_AGE_HOURS}h)"

# Restore test on a copy, in a private temp directory.
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cp -- "$file" "$tmp/restore.db"
python3 - "$tmp/restore.db" <<'PY'
import sqlite3, sys

con = sqlite3.connect(sys.argv[1])
result = con.execute("PRAGMA integrity_check").fetchall()
if result != [("ok",)]:
    sys.exit("integrity_check: %r" % (result,))
for table in ("users", "budgets", "categories", "expenses"):
    try:
        n = con.execute("SELECT count(*) FROM %s" % table).fetchone()[0]
        print("%-10s %d rows" % (table, n))
    except sqlite3.Error as exc:
        sys.exit("cannot read table %s: %s" % (table, exc))
print("restore test ok")
PY
