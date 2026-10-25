#!/usr/bin/env bash
# Runs on the Mac. Pulls the encrypted Bajeti backups from the BACKUP Pi (never from the app Pi).
#
# - The key used here is restricted on the backup Pi to a read-only rsync of the backups folder
#   (rrsync -ro). No Mac credentials live on either Pi, no Pi admin credentials live here.
# - Files are age-encrypted, so the Mac holds ciphertext. The private key stays in the password manager.
# - Every file is checked against its SHA-256 before it is kept. Existing files are never overwritten.
# - DEST_DIR must be on the FileVault volume and OUTSIDE iCloud Desktop/Documents and any synced folder.
#
# Settings (environment):
#   BACKUP_SSH_TARGET   user@host of the backup Pi
#   DEST_DIR            for example $HOME/BajetiBackups
#   SSH_KEY             default $HOME/.ssh/bajeti_mac_pull
#   KNOWN_HOSTS         default $HOME/.ssh/bajeti_mac_pull_known_hosts
set -Eeuo pipefail
umask 077

: "${BACKUP_SSH_TARGET:?set BACKUP_SSH_TARGET}"
: "${DEST_DIR:?set DEST_DIR}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/bajeti_mac_pull}"
KNOWN_HOSTS="${KNOWN_HOSTS:-$HOME/.ssh/bajeti_mac_pull_known_hosts}"

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
die() { log "ERROR: $*" >&2; exit 1; }

case "$DEST_DIR" in
  "$HOME/Desktop"*|"$HOME/Documents"*|*"Mobile Documents"*|*iCloud*|*Dropbox*|*"Google Drive"*|*OneDrive*)
    die "DEST_DIR looks like a synced folder; financial backups must not be cloud-synced" ;;
esac
[ -r "$SSH_KEY" ] && [ -r "$KNOWN_HOSTS" ] || die "ssh key or pinned host key file missing"
mkdir -p "$DEST_DIR"
staging="$(mktemp -d "$DEST_DIR/.incoming.XXXXXX")"
trap 'rm -rf -- "$staging"' EXIT

rsync -rt --no-perms --no-owner --no-group \
  --include='db_backup_*.db.age' --include='db_backup_*.db.age.sha256' --exclude='*' \
  -e "ssh -i $SSH_KEY -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$KNOWN_HOSTS" \
  "$BACKUP_SSH_TARGET:/" "$staging/" || die "rsync failed"

new=0 bad=0
for f in "$staging"/db_backup_*.db.age; do
  [ -e "$f" ] || continue
  base="$(basename "$f")"
  [ -e "$DEST_DIR/$base" ] && continue
  if [ -f "$f.sha256" ] && (cd "$staging" && shasum -a 256 -c "$base.sha256" >/dev/null 2>&1); then
    mv -- "$f" "$DEST_DIR/$base"; mv -- "$f.sha256" "$DEST_DIR/$base.sha256"
    log "kept $base"; new=$((new + 1))
  else
    log "ERROR: checksum failed or missing for $base; not kept" >&2; bad=$((bad + 1))
  fi
done
[ "$bad" -eq 0 ] || die "$bad file(s) failed the checksum"
log "done: $new new, $(find "$DEST_DIR" -maxdepth 1 -name 'db_backup_*.db.age' | wc -l | tr -d ' ') held"
