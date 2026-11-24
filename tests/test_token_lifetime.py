"""Token version, sliding re-issue and the 14-day cap."""
import time
from datetime import timedelta

import pytest
import jwt

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
        reissued = session.maybe_reissue(token, db)
        return reissued[0] if reissued else None
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


# ---- "Keep me signed in" (5 days) ----

def _remember_token(client, email):
    return client.post("/api/auth/token", data={
        "username": email, "password": PASSWORD, "remember": "true"}).json()["access_token"]


def _make_remembered(user, minutes_left, age_seconds=0):
    data = {"sub": user.email, "user_id": user.id, "rem": True,
            "auth_time": int(time.time()) - age_seconds, "ver": user.token_version}
    return TokenService.create_access_token(data, timedelta(minutes=minutes_left))


def test_remembered_login_lasts_five_days(client):
    _, email = make_user(client)

    claims = _decode(_remember_token(client, email))

    assert claims["rem"] is True
    assert 5 * DAY - 60 < claims["exp"] - time.time() <= 5 * DAY


def test_normal_login_is_not_remembered(client):
    _, email = make_user(client)

    claims = _decode(_login_token(client, email))

    assert "rem" not in claims
    assert claims["exp"] - time.time() <= 3600


def test_remembered_token_is_renewed_for_five_more_days(client):
    _, email = make_user(client)
    token = _make_remembered(_user(email), minutes_left=3 * 24 * 60, age_seconds=2 * DAY)

    db = TestingSessionLocal()
    try:
        new, remember = session.maybe_reissue(token, db)
    finally:
        db.close()

    claims = _decode(new)
    assert remember is True and claims["rem"] is True
    assert claims["auth_time"] == _decode(token)["auth_time"]
    assert claims["exp"] - time.time() > 5 * DAY - 60


def test_remembered_token_under_a_day_old_is_not_renewed(client):
    _, email = make_user(client)

    assert _reissue(_make_remembered(_user(email), minutes_left=5 * 24 * 60 - 60)) is None


def test_remembered_login_still_ends_after_fourteen_days(client):
    _, email = make_user(client)
    user = _user(email)

    assert _reissue(_make_remembered(user, minutes_left=24 * 60, age_seconds=14 * DAY + 60)) is None


def test_logout_everywhere_ends_a_remembered_login(client):
    _, email = make_user(client)
    remembered = _remember_token(client, email)

    client.post("/api/auth/logout-all", headers={"Authorization": f"Bearer {remembered}"})

    assert _me(client, remembered).status_code == 401
    assert _reissue(remembered) is None


def test_remembered_cookie_lasts_five_days():
    from fastapi.responses import RedirectResponse
    response = RedirectResponse("/")

    cookies.set_auth_cookies(response, "x", remember=True)

    header = next(v.decode() for k, v in response.raw_headers
                  if k == b"set-cookie" and v.startswith(b"access_token="))
    assert f"Max-Age={5 * DAY}" in header


def test_web_request_renews_a_remembered_cookie_for_five_days(client):
    _, email = make_user(client)
    token = _make_remembered(_user(email), minutes_left=3 * 24 * 60, age_seconds=2 * DAY)

    response = client.get("/", cookies={"access_token": token}, follow_redirects=False)

    cookie = next(v.decode() for k, v in response.headers.raw
                  if k == b"set-cookie" and v.startswith(b"access_token="))
    assert f"Max-Age={5 * DAY}" in cookie
    client.cookies.clear()


@pytest.mark.parametrize("ticked, sent, max_age", [("1", "true", 5 * DAY), (None, None, 3600)])
def test_web_login_passes_the_checkbox_to_the_api(client, monkeypatch, ticked, sent, max_age):
    from app.services import auth_service

    calls = []

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"access_token": "t", "token_type": "bearer"}

    async def fake_post(path, json=None, data=None, headers=None, timeout=10.0):
        calls.append(data)
        return FakeResponse()

    monkeypatch.setattr(auth_service, "post", fake_post)
    form = {"username": "a@example.com", "password": "pw"}
    if ticked:
        form["remember"] = ticked

    response = client.post("/login", data=form, follow_redirects=False)

    assert response.status_code == 303
    assert calls[0].get("remember") == sent
    cookie = next(v.decode() for k, v in response.headers.raw
                  if k == b"set-cookie" and v.startswith(b"access_token="))
    assert f"Max-Age={max_age}" in cookie
    client.cookies.clear()


def test_login_page_has_the_keep_me_signed_in_box(client):
    html = client.get("/login").text

    assert 'name="remember"' in html and "Keep me signed in for 5 days" in html
