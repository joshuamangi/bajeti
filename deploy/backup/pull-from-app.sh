#!/usr/bin/env bash
# Runs on the BACKUP Pi. Pulls the encrypted Bajeti backups from the app Pi, verifies them, and keeps them.
#
# Why pull: the app Pi is internet-facing and the likeliest to be compromised, so it holds no
# credentials for this machine. This machine logs in to the app Pi with a key that the app Pi
# restricts to a read-only rsync of ~/backups/outgoing (rrsync -ro). Nothing here deletes from the
# source, and a deletion on the source never reaches the copies kept here.
#
# The destination may be exFAT: no permissions, no hard links, no journal. So files are plain,
# timestamped and never rewritten, and every file is checked against its SHA-256 before it is kept.
#
# Settings (environment; the systemd unit loads ~/.config/bajeti/pull.env):
#   APP_SSH_TARGET        user@host of the app Pi (placeholder in the repo; the real value is in pull.env)
#   SSH_KEY               private key used for the pull       (default $HOME/.ssh/bajeti_pull)
#   KNOWN_HOSTS           pinned host key file                (default $HOME/.ssh/bajeti_pull_known_hosts)
#   DEST_DIR              where verified copies are kept      (required; a folder on the SSD)
#   RETAIN_DAYS           delete copies older than this here  (default 400)
#   MAX_AGE_HOURS         fail if the newest copy is older    (default 36)
#   MIN_FREE_MB           refuse to run with less free space  (default 500)
#   PULL_PING_URL         optional dead-man's-switch URL, pinged only after a fully verified pull
#
#   pull-from-app.sh [--dry-run]
set -Eeuo pipefail
umask 077

: "${APP_SSH_TARGET:?set APP_SSH_TARGET in pull.env}"
: "${DEST_DIR:?set DEST_DIR in pull.env}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/bajeti_pull}"
KNOWN_HOSTS="${KNOWN_HOSTS:-$HOME/.ssh/bajeti_pull_known_hosts}"
RETAIN_DAYS="${RETAIN_DAYS:-400}"
MAX_AGE_HOURS="${MAX_AGE_HOURS:-36}"
MIN_FREE_MB="${MIN_FREE_MB:-500}"
DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
die() { log "ERROR: $*" >&2; exit 1; }
ping_url() { # failures to ping never change the exit code
  [ -n "${PULL_PING_URL:-}" ] || return 0
  command -v curl >/dev/null 2>&1 || return 0
  curl -fsS -m 10 --retry 3 -o /dev/null "${PULL_PING_URL}${1:-}" 2>/dev/null \
    && log "ping sent${1:+ ($1)}" || log "warning: ping failed"
}

staging=""
cleanup() {
  rc=$?
  [ -z "$staging" ] || rm -rf -- "$staging"
  if [ "$rc" -ne 0 ]; then log "PULL FAILED (exit $rc)" >&2; ping_url "/fail"; fi
  exit "$rc"
}
trap cleanup EXIT

[ -d "$DEST_DIR" ] || die "destination folder does not exist: $DEST_DIR (create it by hand; this script never formats or creates the mount)"
[ -r "$SSH_KEY" ] || die "ssh key not readable: $SSH_KEY"
[ -r "$KNOWN_HOSTS" ] || die "pinned host key file missing: $KNOWN_HOSTS"
case "$DEST_DIR" in *$'\n'*) die "paths may not contain newlines" ;; esac
free_mb="$(df -Pm "$DEST_DIR" | awk 'NR==2 {print $4}')"
[ "${free_mb:-0}" -ge "$MIN_FREE_MB" ] || die "only ${free_mb:-0} MB free in $DEST_DIR (need $MIN_FREE_MB)"

if [ "$DRY_RUN" = 1 ]; then
  log "[dry-run] would pull from the app Pi into $DEST_DIR, keep $RETAIN_DAYS days"
  exit 0
fi

LOCK="$DEST_DIR/.pull.lock"
exec 9>"$LOCK"
flock -n 9 || die "another pull is already running"

staging="$DEST_DIR/.incoming.$$"
mkdir -p "$staging"

# rrsync on the app Pi roots every path at ~/backups/outgoing, so the source is "/".
# --no-perms/--no-owner/--no-group because the destination may be exFAT.
# No --delete: nothing is ever removed here because it disappeared at the source.
log "pulling from the app Pi"
rsync -rt --no-perms --no-owner --no-group \
  --include='db_backup_*.db.age' --include='db_backup_*.db.age.sha256' --exclude='*' \
  -e "ssh -i $SSH_KEY -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$KNOWN_HOSTS" \
  "$APP_SSH_TARGET:/" "$staging/" || die "rsync failed"

sha_check() { # sha_check <dir> <checksum file>
  if command -v sha256sum >/dev/null 2>&1; then (cd "$1" && sha256sum -c -- "$2" >/dev/null 2>&1)
  else (cd "$1" && shasum -a 256 -c -- "$2" >/dev/null 2>&1); fi
}

new=0 bad=0
while IFS= read -r f; do
  base="$(basename "$f")"
  [ -e "$DEST_DIR/$base" ] && continue                      # already kept: never overwrite
  if [ -f "$staging/$base.sha256" ] && sha_check "$staging" "$base.sha256"; then
    mv -- "$staging/$base" "$DEST_DIR/$base"
    mv -- "$staging/$base.sha256" "$DEST_DIR/$base.sha256"
    log "kept $base"
    new=$((new + 1))
  else
    log "ERROR: checksum failed or missing for $base; not kept" >&2
    bad=$((bad + 1))
  fi
done < <(find "$staging" -maxdepth 1 -type f -name 'db_backup_*.db.age' | sort)
[ "$bad" -eq 0 ] || die "$bad file(s) failed the checksum"

# Freshness: the newest copy we hold must be recent, otherwise the app Pi has stopped producing backups.
newest="$(find "$DEST_DIR" -maxdepth 1 -type f -name 'db_backup_*.db.age' | sort | tail -n 1)"
[ -n "$newest" ] || die "no backups held in $DEST_DIR"
now="$(date +%s)"
if mtime="$(stat -c %Y "$newest" 2>/dev/null)"; then :; else mtime="$(stat -f %m "$newest")"; fi
age_h=$(( (now - mtime) / 3600 ))
[ "$age_h" -le "$MAX_AGE_HOURS" ] || die "newest copy is ${age_h}h old (limit ${MAX_AGE_HOURS}h)"

# Retention here is decided here only.
find "$DEST_DIR" -maxdepth 1 -type f \( -name 'db_backup_*.db.age' -o -name 'db_backup_*.db.age.sha256' \) \
  -mtime +"$RETAIN_DAYS" -print0 | while IFS= read -r -d '' old; do
  log "removing copy older than $RETAIN_DAYS days: $(basename "$old")"
  rm -f -- "$old"
done

ping_url ""
log "done: $new new, newest $(basename "$newest") (${age_h}h old)"
