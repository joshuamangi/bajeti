#!/usr/bin/env bash
# Smoke test for a running Bajeti. Run it against a COPY of the data, never the live database:
# it registers a throwaway user.
#
#   scripts/smoke.sh --db <path to the DB file the app is serving> --backup <backup .db file> [--base-url URL]
#
# 1. the site answers
# 2. every table has the same row count as the backup (checked before the throwaway user exists)
# 3. a throwaway user can register, log in and read its own profile
# Refuses a non-loopback --base-url unless --allow-remote is given.
set -Eeuo pipefail

BASE_URL="http://127.0.0.1:8000"; DB=""; BACKUP=""; ALLOW_REMOTE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --base-url) BASE_URL="$2"; shift 2 ;;
    --db) DB="$2"; shift 2 ;;
    --backup) BACKUP="$2"; shift 2 ;;
    --allow-remote) ALLOW_REMOTE=1; shift ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
[ -n "$DB" ] && [ -n "$BACKUP" ] || { echo "usage: smoke.sh --db FILE --backup FILE [--base-url URL]" >&2; exit 2; }
case "$BASE_URL" in
  http://127.0.0.1*|http://localhost*) ;;
  *) [ "$ALLOW_REMOTE" = 1 ] || { echo "refusing $BASE_URL: this registers a user; use a copy on loopback" >&2; exit 2; } ;;
esac

fail() { echo "SMOKE FAILED: $*" >&2; exit 1; }
pass() { echo "ok: $*"; }

# 1. the site answers
code="$(curl -sS -L -o /dev/null -w '%{http_code}' "$BASE_URL/")" || fail "cannot reach $BASE_URL"
[ "$code" = 200 ] || fail "GET / returned $code"
pass "site answers (200)"

# 1b. every /static file the pages reference loads (catches a missing frontend build)
missing=0
for page in / /login; do
  html="$(curl -sS -L "$BASE_URL$page" || true)"
  for asset in $(printf '%s' "$html" | grep -oE '(src|href)="/static/[^"?#]+' | sed -E 's/^(src|href)="//' | sort -u); do
    c="$(curl -sS -o /dev/null -w '%{http_code}' "$BASE_URL$asset" || echo 000)"
    [ "$c" = 200 ] || { echo "  missing asset: $asset ($c)" >&2; missing=$((missing + 1)); }
  done
done
[ "$missing" -eq 0 ] || fail "$missing static file(s) referenced by the pages do not load"
pass "static files referenced by the pages load"

# 2. row counts equal the backup
python3 - "$DB" "$BACKUP" <<'PY' || fail "row counts differ from the backup"
import sqlite3, sys
def counts(path):
    con = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    return {t: con.execute('SELECT count(*) FROM "%s"' % t.replace('"', '""')).fetchone()[0] for t in tables}
a, b = counts(sys.argv[1]), counts(sys.argv[2])
bad = [t for t in sorted(set(a) | set(b)) if a.get(t) != b.get(t)]
for t in sorted(b):
    print("  %-22s db=%-6s backup=%s" % (t, a.get(t), b[t]))
if bad:
    sys.exit("tables that differ: %s" % ", ".join(bad))
PY
pass "row counts equal the backup"

# 3. register, log in, read the profile with a throwaway user
suffix="$(python3 -c 'import secrets; print(secrets.token_hex(4))')"
email="smoke-$suffix@example.invalid"
password="$(python3 -c 'import secrets; print(secrets.token_urlsafe(16))')"
reg="$(curl -sS -o /dev/null -w '%{http_code}' -X POST "$BASE_URL/api/auth/" -H 'Content-Type: application/json' \
  -d "{\"first_name\":\"Smoke\",\"last_name\":\"Test\",\"email\":\"$email\",\"password\":\"$password\",\"security_answer\":\"smoke\"}")"
[ "$reg" = 201 ] || fail "register returned $reg"
token="$(curl -sS -X POST "$BASE_URL/api/auth/token" -d "username=$email" --data-urlencode "password=$password" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')" || fail "login failed"
me="$(curl -sS "$BASE_URL/api/auth/users/me" -H "Authorization: Bearer $token" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["email"])')" || fail "profile read failed"
[ "$me" = "$email" ] || fail "profile email mismatch"
pass "throwaway user registered, logged in, profile read"
echo "SMOKE OK"
