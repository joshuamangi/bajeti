"""One place that sets and clears the browser cookies, so every code path has the same flags."""
from fastapi import Response

from app.config import IS_PRODUCTION, settings


def _max_age() -> int:
    """The cookie lives exactly as long as the token inside it."""
    return settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def _flags() -> dict:
    return {"httponly": True, "samesite": "lax", "secure": IS_PRODUCTION}


def set_auth_cookies(response: Response, access_token: str) -> None:
    response.set_cookie(key="access_token", value=access_token,
                        max_age=_max_age(), **_flags())
    # show_menu is a UI hint, not a secret, so the page script may read it.
    response.set_cookie(key="show_menu", value="1", max_age=_max_age(),
                        httponly=False, samesite="lax", secure=IS_PRODUCTION)


def set_active_budget_cookie(response: Response, budget_id: int) -> None:
    response.set_cookie(key="active_budget_id", value=str(budget_id), **_flags())


def clear_active_budget_cookie(response: Response) -> None:
    """At login, so the default budget opens instead of the one picked last session."""
    response.delete_cookie("active_budget_id", **_flags())


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", **_flags())
    clear_active_budget_cookie(response)
    response.delete_cookie("show_menu", httponly=False,
                           samesite="lax", secure=IS_PRODUCTION)
