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
