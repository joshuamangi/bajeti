# S00: Rotate the leaked SECRET_KEY

**Prompt:** P0  |  **Mode:** claude+human  |  **Depends on:** none  |  **Suggested branch:** `feature/issue-N-rotate-secret-key`

## Goal

Stop trusting the JWT signing key that has been public in git history since September 2025, and make the app refuse to start in production with a missing, weak or known-leaked key.

## Read first (context for this stage)

Read these before doing anything else, in this order.

1. `docs/stages/00-shared-context.md`
2. `docs/stages/HANDOFF.md` (latest entries)
3. `app/config.py`
4. `routers/auth.py`
5. `core/security.py`
6. `.github/workflows/deploy.yml` (how .env is rewritten from GitHub secrets)
7. `docs/deployment-guide.md`

### Outputs of earlier stages this stage relies on

- None.

## Before you start

- Create a GitHub issue for this stage, then a branch `feature/issue-N-rotate-secret-key`.
- Generate the new key yourself on your Mac (`openssl rand -hex 32`) and keep it in your password manager. Never paste a key, .env contents or tokens into a chat.

## The prompt

Work from this prompt as written. Where it says to plan first or wait for approval, stop there. A reference such as "P1a [S01]" means prompt P1a, which is stage file S01 in this folder.

```
Task: rotate the JWT SECRET_KEY, which was committed to git history in September 2025 in a public repo and is still used in production. Treat the old key as burned. Do NOT rewrite git history.

Plan first. Then:
1. Confirm no code path still hardcodes a key. Search the working tree for SECRET_KEY usage. Everything must come from app/config.py via environment.
2. Add a startup check in config: refuse to start in ENVIRONMENT=production if SECRET_KEY is missing, shorter than 32 bytes of entropy, or equals any known-leaked value (store only a SHA-256 hash of the old key in the check, never the key itself).
3. Give me the exact manual steps for: generating a new key (openssl rand -hex 32), updating the GitHub Actions secret, updating the Pi .env (chmod 600), recreating the container, and verifying old tokens are rejected and new logins work. Warn that all users are logged out once.
4. Add a test that an old/forged token is rejected.
5. Add a short docs/security.md section: key rotation procedure and cadence.

Definition of done: tests pass, no secret appears in the diff, and I have a numbered checklist to run on the Pi. Do not execute anything against the Pi.
```

## Watch out for

- Do not rewrite git history. The key is public already; rotating is the fix.
- Rotating logs every user out once. Do it when that is acceptable.
- Do not paste the new or old key into the chat, a commit message or a PR description.

## Your part (Claude cannot or should not do these)

1. Update the GitHub Actions secret with the new key (repo Settings, Secrets and variables, Actions).
2. Deploy the change (merge the PR so deploy.yml rewrites .env) or update the Pi .env by hand with `chmod 600`, then recreate the container.
3. Confirm everyone is logged out once, a fresh login works, and a token signed with the old key is rejected.
4. Check no other place still holds the old key (other environments, local .env files, Cloudflare).

## Done when

- Tests pass, including a test that an old or forged token is rejected.
- Production refuses to start with a missing, short or known-leaked key; only a hash of the old key is in the code.
- docs/security.md has the rotation procedure and cadence.
- You have verified the rotation on production.

The Definition of done inside the prompt is authoritative; this list is a summary.

## Leave behind (later stages read these)

- Startup check in app config and its test
- docs/security.md (key rotation section)

## Finish and hand off

When the work and your part are both done, Claude does this, in order:

1. Checks each item under Done when against evidence it produced in this session (command output, test results, files) and lists anything it could not verify.
2. Appends an entry to `docs/stages/HANDOFF.md` (what was produced, what is unverified, decisions made, open questions), including: Date the key was rotated and confirmation that old tokens are rejected.
3. Sets this stage to `done` in `docs/stages/IMPLEMENTATION.md`. If any of your steps is still open it sets `waiting-on-you` instead and stops.
4. Asks you whether to start the next stage. It does not read the next stage file until you agree.

**Next stage (read only after you agree to start it):** `docs/stages/S01-pi-audit.md`: Pi inventory and necessity audit (both Pis).
