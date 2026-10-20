# Token lifetime and refresh: design for approval

Status: proposal (S10, item 5). Nothing here is implemented. It needs the owner's decision before any code.

## How sessions work today

- Login (`POST /api/auth/token`) returns a JWT that expires after `ACCESS_TOKEN_EXPIRE_MINUTES` (set by the GitHub secret; the tests use 30).
- The web UI keeps the token in the `access_token` cookie. The cookie's `max_age` is a fixed 86400 seconds (24 hours) in `app/utils/cookies.py`, separate from the token's own expiry.
- So the two can disagree. If the secret is 30, the browser keeps a cookie for 24 hours whose token died after 30 minutes, and the user sees a redirect to the login page after 30 minutes. If the secret is longer than 1440, the cookie dies first.
- There is no refresh and no logout on the server: a stolen token works until it expires. `/logout` only deletes the cookie.
- Changing `SECRET_KEY` logs everyone out (that is the only revocation).

## What we want

A stolen cookie should stop working soon, and an owner who is using the app should not be logged out in the middle of entering expenses.

## Options

### A. Short token, sliding re-issue (recommended)

- Token lifetime 60 minutes.
- The web layer re-issues a fresh token (new cookie) on any authenticated page request when the current token has less than half its life left.
- Each token carries `auth_time` (the original login time). Re-issue is refused once `auth_time` is older than 14 days, so a session cannot be extended forever.
- No new table, no new endpoint on the API, no new dependency. The API keeps validating a plain access token.
- Cost: a stolen token is good for up to 60 minutes after the thief's last chance to use it, but it can be extended by the thief too while the owner's session is still valid, up to the 14-day cap. It does not give revocation.

### B. Short access token plus a refresh token

- Access token 15 minutes; a refresh token (random string, stored hashed in a new `refresh_tokens` table with user, expiry, last use, revoked flag) in a second HttpOnly cookie scoped to a refresh path.
- Refresh rotates the token and detects reuse (a reused old refresh token revokes the whole family).
- Gives real revocation: password reset and logout can revoke all refresh tokens.
- Cost: a new table and migration, a new endpoint, more tests, more moving parts for one household. The API clients other than the web UI would need to implement refresh too.

### C. Keep a long token, shorten nothing

Rejected: it keeps the current gap (no way to cut off a stolen token short of rotating `SECRET_KEY`).

## Recommendation

Option A with 60 minutes and a 14-day cap, plus one cheap step toward revocation: add a `token_version` integer to `users` (migration), put it in the token, and bump it on password reset and on a new "log out everywhere" action. A token whose version does not match is rejected. That gives B's revocation without B's table. Move to B only if more users or other clients appear.

## What users would notice

- Logged in on a normal day: nothing. The cookie is refreshed quietly while they use the app.
- Not opening the app for more than an hour: they are sent to the login page (today it is 30 minutes or 24 hours depending on the secret). With the re-issue rule, an hour of inactivity is the expiry.
- After 14 days, one forced login even if they use the app daily.
- After a password reset, every other session is logged out.

## Changes, if approved

1. `ACCESS_TOKEN_EXPIRE_MINUTES` becomes 60 (you change the GitHub secret) and `AUTH_COOKIE_MAX_AGE` follows the setting instead of a constant, so cookie and token cannot disagree.
2. Token payload gets `auth_time` and `ver`; `core/security.py::get_current_user` checks `ver` against `users.token_version`.
3. A small dependency on the web layer's authenticated routes re-issues the cookie when less than half the life is left and `auth_time` is within 14 days.
4. Migration adding `users.token_version` (default 0), with a real downgrade (drop the column).
5. Tests: expired token rejected, re-issue happens only past half life, no re-issue past 14 days, a bumped version rejects an old token, password reset bumps the version.

## Decisions for the owner

- Lifetime: 60 minutes (recommended), or a different number.
- Hard cap: 14 days (recommended), or longer for a phone you trust.
- Option A with `token_version` (recommended) or Option B.

## Not verified

- The value of `ACCESS_TOKEN_EXPIRE_MINUTES` in production (it is a GitHub secret and was not read).
- Whether any client other than the web UI uses the API tokens (the PWA in a later stage may).
