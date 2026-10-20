# Security notes

This repository is public. Never put keys, tokens, `.env` contents, IP addresses or hostnames in code or docs. Use placeholders such as `<PI_APP_HOST>`.

## JWT signing key (`SECRET_KEY`)

Where it lives: the `SECRET_KEY` GitHub Actions secret, and the `.env` file on the host that runs the app. The deploy workflow rewrites `.env` from the secret on every deploy, so the two must always match.

Startup check (`app/config.py`): with `ENVIRONMENT=production` the app refuses to start if the key is shorter than 43 characters or matches a known-leaked value. The leaked values are stored only as SHA-256 hashes in `LEAKED_SECRET_KEY_HASHES`. Outside production it logs a warning instead.

A key committed to git history is burned for good. Rotate it; do not rewrite history.

### Rotation procedure

Rotating logs every user out once.

1. Generate a key on your own machine: `openssl rand -hex 32`. Keep it in a password manager. Do not paste it into a chat, a commit, a PR or an issue.
2. Update the GitHub secret: repo Settings, Secrets and variables, Actions, `SECRET_KEY`.
3. Update `.env` on the host, then lock it down and recreate the container:
   - edit the `SECRET_KEY=` line in `<PROJECT_DIR>/.env`
   - `chmod 600 .env`
   - `docker compose up -d --force-recreate bajeti_app`
4. Verify:
   - a fresh login works
   - an existing browser session is sent back to the login page
   - the container is healthy: `docker compose ps` and `docker compose logs --tail=50 bajeti_app` show no config errors
5. If the key was exposed, add `sha256(old_key)` to `LEAKED_SECRET_KEY_HASHES` in `app/config.py`:
   `printf %s "$OLD_KEY" | shasum -a 256`
6. Check nothing else still holds the old key: other `.env` files, other environments, password manager entries.

### Cadence

Rotate at least once a year, and immediately if the key may have been seen by anyone else (a repo leak, a lost laptop, a shared screen).

### Deploy ordering

Rotate (steps 1 to 3) before merging a change that adds or tightens the startup check. Otherwise the new code refuses to start with the old key and the site is down until `.env` is fixed.

## Registration switch (`REGISTRATION_OPEN`)

Registration is closed by default: `POST /api/auth/`, `GET` and `POST /register` return 404 and the login page hides the link. To add someone:

1. GitHub, Settings, Secrets and variables, Actions, Variables: create `REGISTRATION_OPEN` = `true`, then run the deploy (merge any PR or re-run the last deploy).
2. Register the person.
3. Set the variable back to `false` (or delete it) and deploy again.

The deploy writes `REGISTRATION_OPEN` into `.env` from that variable and falls back to `false` when it is not set.

## Login and reset limits

Failed logins and password resets are counted in memory (`core/rate_limit.py`): 5 failures per 15 minutes per address and email for login, 5 per hour for reset, and 30 / 20 per address across emails. Over the limit the API answers 429 with `Retry-After`. Counters reset when the app restarts. The client address comes from `CF-Connecting-IP`, which is trustworthy only because the app port is bound to loopback and reached through the tunnel; the web pages forward it when they call the API.

Password reset answers "Incorrect email or security answer" for an unknown email, a missing answer and a wrong answer alike.

## Security answers

Stored as a bcrypt hash of the stripped, case-folded answer (migration `b7c1d2e3f4a5`). It cannot be shown again: the profile page leaves the field blank and a new value replaces the old one. The migration cannot be reversed; take a backup before running it on production.
