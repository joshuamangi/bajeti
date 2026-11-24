"""Sliding session: a fresh cookie while the user is active, with a hard cap."""
import time
from typing import Optional, Tuple

from fastapi import Request
from sqlalchemy.orm import Session

from app.utils.cookies import set_auth_cookies
from data.db.db import get_db
from services.token_service import TokenService
from services.user_service import UserService

SESSION_MAX_AGE_SECONDS = 14 * 86400  # the original login may not be extended past this
REMEMBER_RENEW_AFTER_SECONDS = 86400  # a remembered token is renewed at most once a day

_SKIP_PREFIXES = ("/api", "/static")


def maybe_reissue(token: str, db: Session) -> Optional[Tuple[str, bool]]:
    """Return (new token, remembered) if this one is due for renewal, else None.

    A normal token is due past half its life. A remembered one (5 days) is due once it is a
    day old, so 5 days without opening the app is what signs the user out.

    No new token for: an expired or invalid token, one without `auth_time` (issued before
    this existed; it simply runs out), one whose login is over 14 days old, or one whose
    version no longer matches the user (logged out everywhere).
    """
    payload = TokenService.decode_token(token)
    if not payload:
        return None
    now = time.time()
    remember = bool(payload.get("rem"))
    lifetime = TokenService.lifetime(remember).total_seconds()
    renew_below = lifetime - REMEMBER_RENEW_AFTER_SECONDS if remember else lifetime / 2
    if payload.get("exp", 0) - now > renew_below:
        return None
    auth_time = payload.get("auth_time")
    if auth_time is None or now - auth_time > SESSION_MAX_AGE_SECONDS:
        return None
    user = UserService.get_user_by_id(db, payload.get("user_id"))
    if (not user or user.email != payload.get("sub")
            or payload.get("ver", 0) != user.token_version):
        return None
    data = {"sub": user.email, "user_id": user.id,
            "auth_time": auth_time, "ver": user.token_version}
    if remember:
        data["rem"] = True
    new_token = TokenService.create_access_token(
        data=data, expires_delta=TokenService.lifetime(remember))
    return new_token, remember


def _sets_access_token(response) -> bool:
    return any(k == b"set-cookie" and v.startswith(b"access_token=")
               for k, v in response.raw_headers)


async def renew_session_cookie(request: Request, call_next):
    """HTTP middleware for the web pages (not the JSON API, whose clients hold their own token)."""
    response = await call_next(request)
    token = request.cookies.get("access_token")
    if (not token or request.url.path.startswith(_SKIP_PREFIXES)
            or _sets_access_token(response)):
        return response
    # Use the same database dependency as the routes (tests override it).
    db_dependency = request.app.dependency_overrides.get(get_db, get_db)
    generator = db_dependency()
    db = next(generator)
    try:
        reissued = maybe_reissue(token, db)
    finally:
        generator.close()
    if reissued:
        new_token, remember = reissued
        set_auth_cookies(response, new_token, remember=remember)
    return response
