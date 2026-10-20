#!/usr/bin/env bash
# Monthly drift check, run from the Mac (never on a Pi): ansible-playbook --check --diff shows any
# change on a Pi that Ansible does not describe. Reports by notification and log; changes nothing.
#
#   scripts/drift-check.sh [--limit app|backup]
#
# Needs infra/ansible/inventory/production.ini and group_vars (git-ignored) and, if used, the vault
# password in $ANSIBLE_VAULT_PASSWORD_FILE.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/infra/ansible"
LIMIT="${2:-all}"
[ "${1:-}" = "--limit" ] || LIMIT="all"
LOG="${HOME}/Library/Logs/bajeti-drift-check.log"
out="$(ansible-playbook playbooks/site.yml --check --diff --limit "$LIMIT" 2>&1)" || rc=$?
printf '%s\n%s\n' "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) limit=$LIMIT" "$out" >>"$LOG"
recap="$(printf '%s\n' "$out" | grep -E '^[A-Za-z0-9_]+ +: ok=' || true)"
changed="$(printf '%s\n' "$recap" | sed -E 's/.*changed=([0-9]+).*/\1/' | awk '{s+=$1} END {print s+0}')"
failed="$(printf '%s\n' "$recap" | sed -E 's/.*failed=([0-9]+).*/\1/' | awk '{s+=$1} END {print s+0}')"
msg="Bajeti drift check: $changed change(s), $failed failure(s). See $LOG"
echo "$msg"
if [ "${changed:-0}" -gt 0 ] || [ "${failed:-0}" -gt 0 ] || [ "${rc:-0}" -ne 0 ]; then
  osascript -e "display notification \"$msg\" with title \"Bajeti\"" >/dev/null 2>&1 || true
  exit 1
fi
