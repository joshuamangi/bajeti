#!/usr/bin/env bash
# Restore test for one backup file from any tier. Works on a private copy and never touches a live database.
#
#   backup-restore-test.sh <backup file> [age identity file]
#
# A .db.age file needs the identity (private key) file; fetch it from the password manager, point
# this script at it, and delete it afterwards. Checks the SHA-256 file next to the backup if present,
# decrypts, runs PRAGMA integrity_check, and prints row counts and the elapsed seconds.
# Record the result in docs/backup-restore-log.md (tier, date, seconds; no secrets).
set -Eeuo pipefail
umask 077

file="${1:?usage: backup-restore-test.sh <backup file> [age identity file]}"
identity="${2:-}"
[ -s "$file" ] || { echo "RESTORE TEST FAILED: $file missing or empty" >&2; exit 1; }
start="$(date +%s)"
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT

if [ -f "$file.sha256" ]; then
  dir="$(cd "$(dirname "$file")" && pwd)"; base="$(basename "$file")"
  if command -v sha256sum >/dev/null 2>&1; then (cd "$dir" && sha256sum -c "$base.sha256")
  else (cd "$dir" && shasum -a 256 -c "$base.sha256"); fi
else
  echo "note: no .sha256 file next to the backup; checksum not checked"
fi

case "$file" in
  *.age)
    [ -r "$identity" ] || { echo "RESTORE TEST FAILED: an age identity file is needed for $file" >&2; exit 1; }
    age -d -i "$identity" -o "$tmp/restore.db" "$file" ;;
  *) cp -- "$file" "$tmp/restore.db" ;;
esac

python3 - "$tmp/restore.db" <<'PY'
import sqlite3, sys
con = sqlite3.connect(sys.argv[1])
result = con.execute("PRAGMA integrity_check").fetchall()
if result != [("ok",)]:
    sys.exit("RESTORE TEST FAILED: integrity_check: %r" % (result,))
tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
if not tables:
    sys.exit("RESTORE TEST FAILED: no tables")
for t in tables:
    print("%-24s %d rows" % (t, con.execute('SELECT count(*) FROM "%s"' % t.replace('"', '""')).fetchone()[0]))
PY
echo "restore test ok in $(( $(date +%s) - start ))s: $(basename "$file")"
