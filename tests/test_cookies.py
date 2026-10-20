"""Cookie flags on every code path that sets or clears the session cookies."""
import pathlib

from fastapi.responses import RedirectResponse

from app.utils import cookies

HANDLERS = pathlib.Path("app/handlers")


def _set_cookie_headers(response):
    return [v.decode() for k, v in response.raw_headers if k == b"set-cookie"]


def test_auth_cookies_are_httponly_lax_and_secure_in_production(monkeypatch):
    monkeypatch.setattr(cookies, "IS_PRODUCTION", True)
    response = RedirectResponse("/dashboard")

    cookies.set_auth_cookies(response, "token-value")

    access = next(h for h in _set_cookie_headers(response) if h.startswith("access_token="))
    assert "HttpOnly" in access
    assert "Secure" in access
    assert "SameSite=lax" in access


def test_active_budget_cookie_flags(monkeypatch):
    monkeypatch.setattr(cookies, "IS_PRODUCTION", True)
    response = RedirectResponse("/dashboard")

    cookies.set_active_budget_cookie(response, 7)

    header = _set_cookie_headers(response)[0]
    assert header.startswith("active_budget_id=7")
    assert "HttpOnly" in header and "Secure" in header and "SameSite=lax" in header


def test_secure_flag_off_outside_production(monkeypatch):
    monkeypatch.setattr(cookies, "IS_PRODUCTION", False)
    response = RedirectResponse("/dashboard")

    cookies.set_auth_cookies(response, "token-value")

    assert all("Secure" not in h for h in _set_cookie_headers(response))


def test_clearing_cookies_uses_the_same_attributes(monkeypatch):
    monkeypatch.setattr(cookies, "IS_PRODUCTION", True)
    response = RedirectResponse("/login")

    cookies.clear_auth_cookies(response)

    for header in _set_cookie_headers(response):
        assert "Secure" in header and "SameSite=lax" in header


def test_handlers_do_not_set_cookies_directly():
    """Every cookie goes through app/utils/cookies.py so no code path misses a flag."""
    offenders = [
        f"{path}:{number}"
        for path in HANDLERS.glob("*.py")
        for number, line in enumerate(path.read_text().splitlines(), 1)
        if ".set_cookie(" in line or ".delete_cookie(" in line
    ]
    assert offenders == []
