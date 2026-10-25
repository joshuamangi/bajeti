# S10: App security fixes with tests

**Prompt:** P6  |  **Mode:** claude  |  **Depends on:** S00  |  **Suggested branch:** `feature/issue-N-app-security-fixes`

## Goal

Close the app-level security gaps: allocation ownership checks, hashed security answers, cookie flags, rate limiting, security headers.

## Read first (context for this stage)

Read these before doing anything else, in this order.

1. `docs/stages/00-shared-context.md`
2. `docs/stages/HANDOFF.md` (latest entries)
3. `routers/allocations.py` and the allocation and budget services
4. `routers/auth.py`, routers/users.py, core/security.py, schema for users
5. `tests/conftest.py` and the existing auth and users tests
6. `app/handlers` and app/utils where cookies are set

### Outputs of earlier stages this stage relies on

- S00 (rotated key)
- S06 plan if you did it first

## Before you start

- One commit per fix, each with a failing-before and passing-after test.

## The prompt

Work from this prompt as written. Where it says to plan first or wait for approval, stop there. A reference such as "P1a [S01]" means prompt P1a, which is stage file S01 in this folder.

```
Task: fix these app-level security issues, one commit each, each with tests. Plan first.

1. Allocation update/delete endpoints filter only by budget_id, not by current user. Add ownership checks via BudgetService.get_budget_by_id and write cross-user tests (user B gets 404/403 and nothing changes).
2. users.security_answer is stored in plain text. Hash it (bcrypt via passlib, normalised: strip + casefold), add an Alembic migration that rehashes existing values safely (a data migration cannot reverse hashes, so document the downgrade limits explicitly), and keep password reset working. Add a test.
3. Cookies: set Secure (in production), HttpOnly, SameSite=Lax on access_token and active_budget_id in every code path.
4. Rate limiting on /auth/token and /users/password/reset (in-memory limiter is fine for a single process; justify the choice). Return generic errors so emails cannot be enumerated.
5. Token lifetime: shorten the access token and propose a refresh approach, but do not implement a refresh flow without showing me the design first.
6. Set a security headers middleware (CSP compatible with the current templates, X-Content-Type-Options, Referrer-Policy, frame protection).

Definition of done: full pytest passes, each fix has a failing-before / passing-after test, and a summary table of what changed and what behaviour users will notice.
```

## Watch out for

- Hashing security answers is one-way. Test the migration on a copy and read the downgrade notes before running it on production.
- Each fix gets its own failing-first test, including a cross-user test.
- Changing cookie flags or token lifetime logs users out or changes behaviour. List what users will notice.

## Your part (Claude cannot or should not do these)

1. Review each commit.
2. Run the security-answer migration against a copy of the production database. Hashing cannot be reversed, so read the downgrade notes.
3. Decide the token lifetime and approve the refresh design before any refresh flow is built.

## Done when

- Full pytest passes.
- Each fix has its own test.
- A summary table of what changed and what users will notice.

The Definition of done inside the prompt is authoritative; this list is a summary.

## Leave behind (later stages read these)

- Tests and fixes
- Alembic migration for security answers

## Finish and hand off

When the work and your part are both done, Claude does this, in order:

1. Checks each item under Done when against evidence it produced in this session (command output, test results, files) and lists anything it could not verify.
2. Appends an entry to `docs/stages/HANDOFF.md` (what was produced, what is unverified, decisions made, open questions), including: The cross-user test pattern you want every later stage to reuse.
3. Sets this stage to `done` in `docs/stages/IMPLEMENTATION.md`. If any of your steps is still open it sets `waiting-on-you` instead and stops.
4. Asks you whether to start the next stage. It does not read the next stage file until you agree.

**Next stage (read only after you agree to start it):** `docs/stages/S11-targets-e0.md`: E0 Targets (#101, #103 to #106).
