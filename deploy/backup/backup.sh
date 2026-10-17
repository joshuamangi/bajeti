#!/usr/bin/env bash
# Nightly Bajeti database backup: a consistent copy, checked, pruned, copied off the Pi.
#
# - Uses the SQLite backup API (through python3, because the Pi has no sqlite3 binary), which is
#   safe while the app is running. A plain `cp` of a live database is not.
# - The copy is kept only if PRAGMA integrity_check says "ok". It is written to a hidden .partial
#   file first and renamed, so a half-written backup never looks like a good one.
# - Every step is checked. Any failure exits non-zero, so systemd marks the run failed and the
#   OnFailure= unit fires.
# - A lock stops two runs overlapping.
#
# Settings come from the environment (the systemd unit loads ~/.config/bajeti/backup.env):
#   DB_PATH               live database      (default $HOME/projects/bajeti/data/db/data/bajeti.db)
#   BACKUP_DIR            local copies       (default $HOME/backups/db_backups)
#   BACKUP_KEEP           copies to keep     (default 365; each copy is small, and pruning is
#                         permanent, so err on the side of keeping more)
#   S3_BUCKET             s3://bucket[/prefix] for the off-device copy (empty = skip)
#   BACKUP_COPY_COMMAND   optional second copy; shell command run with the new file as "$1"
#   BACKUP_PING_URL       optional dead-man's-switch URL (for example a healthchecks.io check);
#                         it is pinged on success and at <URL>/fail on failure. The URL is never logged.
#   BACKUP_MIN_FREE_MB    refuse to run with less free space than this (default 200)
#
#   backup.sh [--dry-run]
set -Eeuo pipefail
umask 077

DB_PATH="${DB_PATH:-$HOME/projects/bajeti/data/db/data/bajeti.db}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups/db_backups}"
KEEP="${BACKUP_KEEP:-365}"
S3_BUCKET="${S3_BUCKET:-}"
MIN_FREE_MB="${BACKUP_MIN_FREE_MB:-200}"
DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
die() { log "ERROR: $*" >&2; exit 1; }

ping_url() { # ping_url [suffix]; failures to ping never change the exit code
  [ -n "${BACKUP_PING_URL:-}" ] || return 0
  command -v curl >/dev/null 2>&1 || return 0
  curl -fsS -m 10 --retry 3 -o /dev/null "${BACKUP_PING_URL}${1:-}" 2>/dev/null \
    && log "ping sent${1:+ ($1)}" || log "warning: ping failed"
}

partial=""
lockdir=""
cleanup() {
  rc=$? # must be the first statement: it is the script's real exit code
  [ -z "$partial" ] || rm -f "$partial"
  [ -z "$lockdir" ] || rmdir "$lockdir" 2>/dev/null || true
  if [ "$rc" -ne 0 ]; then
    log "BACKUP FAILED (exit $rc)" >&2
    ping_url "/fail"
  fi
  exit "$rc"
}
trap cleanup EXIT

# --- sanity checks -----------------------------------------------------------------------
# The Pi has no battery clock; a boot before the network time sync reports 1970.
[ "$(date +%Y)" -ge 2025 ] || die "system clock looks wrong ($(date)); refusing to name a backup with it"
command -v python3 >/dev/null 2>&1 || die "python3 is required"
[ -f "$DB_PATH" ] || die "database not found: $DB_PATH"
case "$DB_PATH$BACKUP_DIR" in *$'\n'*) die "paths may not contain newlines" ;; esac
[[ "$KEEP" =~ ^[0-9]+$ ]] && [ "$KEEP" -ge 1 ] || die "BACKUP_KEEP must be a positive number"

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR" 2>/dev/null || log "note: could not set permissions on $BACKUP_DIR"

free_mb="$(df -Pm "$BACKUP_DIR" | awk 'NR==2 {print $4}')"
[ "${free_mb:-0}" -ge "$MIN_FREE_MB" ] || die "only ${free_mb:-0} MB free in $BACKUP_DIR (need $MIN_FREE_MB)"

if [ "$DRY_RUN" = 1 ]; then
  log "[dry-run] would back up $DB_PATH to $BACKUP_DIR, keep $KEEP, s3='${S3_BUCKET:-none}'"
  exit 0
fi

# --- lock --------------------------------------------------------------------------------
LOCK="$BACKUP_DIR/.backup.lock"
if command -v flock >/dev/null 2>&1; then
  exec 9>"$LOCK"
  flock -n 9 || die "another backup is already running"
else # no flock (for example macOS): fall back to an atomic mkdir lock
  mkdir "$LOCK.d" 2>/dev/null || die "another backup is already running ($LOCK.d exists)"
  lockdir="$LOCK.d"
fi

# --- backup ------------------------------------------------------------------------------
name="db_backup_$(date -u +%Y-%m-%d_%H-%M-%S).db"
final="$BACKUP_DIR/$name"
while [ -e "$final" ]; do # one-second names: wait if two runs land in the same second
  sleep 1
  name="db_backup_$(date -u +%Y-%m-%d_%H-%M-%S).db"
  final="$BACKUP_DIR/$name"
done
partial="$BACKUP_DIR/.$name.partial"

log "backup $DB_PATH -> $final"
python3 - "$DB_PATH" "$partial" <<'PY'
import sqlite3, sys

src_path, dst_path = sys.argv[1], sys.argv[2]
src = sqlite3.connect(src_path, timeout=10)
dst = sqlite3.connect(dst_path)
try:
    src.backup(dst)  # consistent snapshot even while the app writes
    dst.commit()
    result = dst.execute("PRAGMA integrity_check").fetchall()
    if result != [("ok",)]:
        sys.exit("integrity check of the new backup failed: %r" % (result,))
    tables = dst.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    if tables < 1:
        sys.exit("the new backup contains no tables")
    print("integrity ok, %d tables" % tables)
finally:
    dst.close()
    src.close()
PY
mv "$partial" "$final"
partial=""
touch "$BACKUP_DIR/.last_backup_ok"
log "backup ok: $final ($(wc -c <"$final" | tr -d ' ') bytes)"

# --- prune old local copies (only after a good backup) ------------------------------------
# Names carry a UTC timestamp, so a name sort is a date sort.
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'db_backup_*.db' | sort -r | tail -n +"$((KEEP + 1))" |
  while IFS= read -r old; do
    log "removing old backup $old"
    rm -f -- "$old"
  done

# --- off-device copy (S3) -----------------------------------------------------------------
if [ -n "$S3_BUCKET" ]; then
  command -v aws >/dev/null 2>&1 || die "S3_BUCKET is set but the aws CLI is missing"
  rest="${S3_BUCKET#s3://}"
  bucket="${rest%%/*}"
  prefix="${rest#"$bucket"}"; prefix="${prefix#/}"; prefix="${prefix%/}"
  key="${prefix:+$prefix/}$name"
  log "uploading to s3://$bucket/$key"
  aws s3 cp --only-show-errors --cli-connect-timeout 20 --cli-read-timeout 120 \
    "$final" "s3://$bucket/$key" || die "S3 upload failed"
  local_size="$(wc -c <"$final" | tr -d ' ')"
  remote_size="$(aws s3api head-object --bucket "$bucket" --key "$key" \
    --query ContentLength --output text)" || die "could not read the uploaded object back"
  [ "$remote_size" = "$local_size" ] || die "S3 size mismatch: local $local_size, remote $remote_size"
  log "s3 copy verified ($remote_size bytes)"
else
  log "no S3_BUCKET set: skipping the S3 copy"
fi

# --- optional second copy -----------------------------------------------------------------
if [ -n "${BACKUP_COPY_COMMAND:-}" ]; then
  log "running BACKUP_COPY_COMMAND"
  sh -c "$BACKUP_COPY_COMMAND" bajeti-backup "$final" || die "BACKUP_COPY_COMMAND failed"
fi

ping_url ""
log "done"
