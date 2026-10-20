"""Token version, sliding re-issue and the 14-day cap."""
import time
from datetime import timedelta

import pytest
from jose import jwt

from app.config import settings
from app.utils import cookies
from core import session
from data.db.models.models import User
from services.token_service import TokenService
from tests.conftest import TestingSessionLocal
from tests.helpers import PASSWORD, make_user

DAY = 86400


@pytest.fixture(autouse=True)
def sixty_minutes(monkeypatch):
    monkeypatch.setattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60)


def _decode(token):
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def _login_token(client, email, password=PASSWORD):
    return client.post("/api/auth/token",
                       data={"username": email, "password": password}).json()["access_token"]


def _user(email):
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == email).one()
        db.expunge(user)
        return user
    finally:
        db.close()


def _make_token(user, minutes_left, age_seconds=0, version=None, with_claims=True):
    data = {"sub": user.email, "user_id": user.id}
    if with_claims:
        data["auth_time"] = int(time.time()) - age_seconds
        data["ver"] = user.token_version if version is None else version
    return TokenService.create_access_token(data, timedelta(minutes=minutes_left))


def _reissue(token):
    db = TestingSessionLocal()
    try:
        return session.maybe_reissue(token, db)
    finally:
        db.close()


def _me(client, token):
    return client.get("/api/auth/users/me", headers={"Authorization": f"Bearer {token}"})


# ---- token content and version check ----

def test_login_token_carries_auth_time_and_version(client):
    _, email = make_user(client)

    claims = _decode(_login_token(client, email))

    assert claims["ver"] == 0
    assert abs(claims["auth_time"] - time.time()) < 30
    assert 3500 < claims["exp"] - time.time() <= 3600


def test_token_with_an_old_version_is_rejected(client):
    _, email = make_user(client)
    token = _login_token(client, email)
    assert _me(client, token).status_code == 200

    db = TestingSessionLocal()
    db.query(User).filter(User.email == email).update({"token_version": 1})
    db.commit()
    db.close()

    assert _me(client, token).status_code == 401


def test_token_without_a_version_counts_as_version_zero(client):
    """Tokens issued before this change must keep working through the deploy."""
    _, email = make_user(client)
    legacy = _make_token(_user(email), minutes_left=30, with_claims=False)

    assert _me(client, legacy).status_code == 200


def test_password_reset_logs_out_other_sessions(client):
    _, email = make_user(client, answer="Rover")
    old = _login_token(client, email)

    reset = client.post("/api/users/password/reset", json={
        "email": email, "security_answer": "Rover", "new_password": "newpass12345"})

    assert reset.status_code == 200
    assert _me(client, old).status_code == 401
    assert _me(client, _login_token(client, email, "newpass12345")).status_code == 200


def test_logout_everywhere_invalidates_every_token(client):
    _, email = make_user(client)
    first, second = _login_token(client, email), _login_token(client, email)

    response = client.post("/api/auth/logout-all",
                           headers={"Authorization": f"Bearer {first}"})

    assert response.status_code == 204
    assert _me(client, first).status_code == 401
    assert _me(client, second).status_code == 401
    assert _me(client, _login_token(client, email)).status_code == 200


def test_logout_everywhere_needs_a_login(client):
    assert client.post("/api/auth/logout-all").status_code == 401


# ---- sliding re-issue ----

def test_token_past_half_its_life_is_reissued_with_the_same_login_time(client):
    _, email = make_user(client)
    user = _user(email)
    token = _make_token(user, minutes_left=20, age_seconds=2 * DAY)

    new = _reissue(token)

    assert new and new != token
    old_claims, new_claims = _decode(token), _decode(new)
    assert new_claims["auth_time"] == old_claims["auth_time"]
    assert new_claims["ver"] == old_claims["ver"]
    assert new_claims["exp"] - time.time() > 3500


def test_fresh_token_is_not_reissued(client):
    _, email = make_user(client)

    assert _reissue(_make_token(_user(email), minutes_left=50)) is None


def test_no_reissue_after_fourteen_days(client):
    _, email = make_user(client)
    user = _user(email)

    assert _reissue(_make_token(user, minutes_left=10, age_seconds=14 * DAY + 60)) is None
    assert _reissue(_make_token(user, minutes_left=10, age_seconds=13 * DAY)) is not None


def test_no_reissue_for_a_revoked_or_legacy_token(client):
    _, email = make_user(client)
    user = _user(email)

    assert _reissue(_make_token(user, minutes_left=10, version=5)) is None
    assert _reissue(_make_token(user, minutes_left=10, with_claims=False)) is None
    assert _reissue("not-a-token") is None


def test_no_reissue_for_an_expired_token(client):
    _, email = make_user(client)

    assert _reissue(_make_token(_user(email), minutes_left=-5)) is None


def test_web_request_gets_a_fresh_cookie_when_the_token_is_old(client):
    _, email = make_user(client)
    token = _make_token(_user(email), minutes_left=20)

    response = client.get("/", cookies={"access_token": token}, follow_redirects=False)

    cookie = next(v.decode() for k, v in response.headers.raw
                  if k == b"set-cookie" and v.startswith(b"access_token="))
    assert "Max-Age=3600" in cookie
    assert token not in cookie


def test_web_request_with_a_fresh_token_gets_no_new_cookie(client):
    _, email = make_user(client)
    token = _make_token(_user(email), minutes_left=55)

    response = client.get("/", cookies={"access_token": token}, follow_redirects=False)

    assert not [v for k, v in response.headers.raw
                if k == b"set-cookie" and v.startswith(b"access_token=")]


def test_cookie_lifetime_follows_the_setting(monkeypatch):
    from fastapi.responses import RedirectResponse
    monkeypatch.setattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 45)
    response = RedirectResponse("/")

    cookies.set_auth_cookies(response, "x")

    header = next(v.decode() for k, v in response.raw_headers
                  if k == b"set-cookie" and v.startswith(b"access_token="))
    assert "Max-Age=2700" in header


def test_web_logout_all_calls_the_api_and_clears_the_cookies(client, monkeypatch):
    from app.services import auth_service

    calls = []

    async def fake_post(path, json=None, data=None, headers=None, timeout=10.0):
        calls.append((path, headers))

    monkeypatch.setattr(auth_service, "post", fake_post)
    client.cookies.set("access_token", "the-token")

    response = client.post("/logout-all", follow_redirects=False)

    assert response.status_code == 303 and response.headers["location"] == "/login"
    assert calls == [("/auth/logout-all", {"Authorization": "Bearer the-token"})]
    cleared = [v.decode() for k, v in response.headers.raw if k == b"set-cookie"]
    assert any(c.startswith("access_token=") and "Max-Age=0" in c for c in cleared)
    client.cookies.clear()
