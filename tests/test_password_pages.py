"""Web pages for forgot password, change password, reset links and Admin.

The API calls are replaced, so these check what each page sends and how it answers.
"""
from datetime import timedelta

import httpx
from fastapi.testclient import TestClient

from app.handlers import admin_handlers, auth_handlers, dashboard_handlers
from main import app
from services.token_service import TokenService


def signed_in():
    client = TestClient(app, follow_redirects=False)
    token = TokenService.create_access_token(
        {"sub": "pages@example.com", "user_id": 1}, timedelta(minutes=5))
    client.cookies.set("access_token", token)
    return client


def fake(monkeypatch, module, name, status_code=200, json=None, calls=None):
    async def call(*args, **kwargs):
        if calls is not None:
            calls.append((args, kwargs))
        return httpx.Response(status_code, json=json if json is not None else {})
    monkeypatch.setattr(module, name, call)


def test_forgot_password_form_calls_the_api_and_logs_in(monkeypatch):
    calls = []
    fake(monkeypatch, auth_handlers, "svc_reset_password", calls=calls)
    fake(monkeypatch, auth_handlers, "auth_login", json={"access_token": "new-token"})
    client = TestClient(app, follow_redirects=False)

    r = client.post("/forgot_password", data={
        "email": "a@example.com", "security_answer": "Rex",
        "new_password": "simple", "confirm_password": "simple"})

    assert calls and calls[0][0][:3] == ("a@example.com", "Rex", "simple")
    assert r.status_code == 303 and r.headers["location"] == "/dashboard"


def test_forgot_password_wrong_answer_shows_the_error(monkeypatch):
    fake(monkeypatch, auth_handlers, "svc_reset_password", 400,
         {"detail": "Incorrect email or security answer"})
    r = TestClient(app).post("/forgot_password", data={
        "email": "a@example.com", "security_answer": "x",
        "new_password": "simple", "confirm_password": "simple"})
    assert "Incorrect email or security answer" in r.text


def test_short_password_is_refused_before_the_api(monkeypatch):
    calls = []
    fake(monkeypatch, auth_handlers, "svc_reset_password", calls=calls)
    r = TestClient(app).post("/forgot_password", data={
        "email": "a@example.com", "security_answer": "Rex",
        "new_password": "abc", "confirm_password": "abc"})
    assert "Use at least 6 characters" in r.text and not calls


def test_change_password_sets_the_new_cookie(monkeypatch):
    fake(monkeypatch, dashboard_handlers, "svc_change_password", json={"access_token": "fresh"})
    r = signed_in().post("/profile/password", data={
        "current_password": "old-pass", "new_password": "simple", "confirm_password": "simple"})
    assert r.status_code == 303 and r.headers["location"].startswith("/profile")
    assert "access_token=fresh" in r.headers["set-cookie"]


def test_change_password_wrong_current_password(monkeypatch):
    fake(monkeypatch, dashboard_handlers, "svc_change_password", 400, {"detail": "x"})
    r = signed_in().post("/profile/password", data={
        "current_password": "nope", "new_password": "simple", "confirm_password": "simple"})
    assert r.status_code == 200 and "Current password is incorrect" in r.text


def test_security_question_sends_the_password(monkeypatch):
    calls = []
    fake(monkeypatch, dashboard_handlers, "update_profile", calls=calls)
    r = signed_in().post("/profile/security-question", data={
        "security_answer": "Rex", "current_password": "pass1234"})
    assert r.status_code == 303
    assert calls[0][0][1] == {"security_answer": "Rex", "current_password": "pass1234"}


def test_reset_link_page_keeps_token_out_of_the_url(monkeypatch):
    calls = []
    fake(monkeypatch, auth_handlers, "svc_use_reset_link", json={"access_token": "fresh"}, calls=calls)
    client = TestClient(app, follow_redirects=False)

    assert client.get("/reset").status_code == 200
    r = client.post("/reset", data={"token": "tok", "new_password": "simple", "confirm_password": "simple"})

    assert calls[0][0][:2] == ("tok", "simple")
    assert r.status_code == 303 and "tok" not in r.headers["location"]
    assert "access_token=fresh" in r.headers["set-cookie"]


def test_used_link_keeps_token_in_the_form(monkeypatch):
    fake(monkeypatch, auth_handlers, "svc_use_reset_link", 400, {"detail": "This link has expired"})
    r = TestClient(app).post("/reset", data={
        "token": "tok-123", "new_password": "simple", "confirm_password": "nomatch"})
    assert "Passwords do not match" in r.text and 'value="tok-123"' in r.text


def test_members_see_owner_only(monkeypatch):
    fake(monkeypatch, admin_handlers, "fetch_members", 404, {"detail": "Not found"})
    r = signed_in().get("/admin")
    assert r.status_code == 200 and "Owner only" in r.text


def test_owner_sees_link_once_after_reset(monkeypatch):
    members = [{"id": 1, "first_name": "Owner", "last_name": "One", "email": "o@example.com",
                "is_owner": True, "has_security_answer": True, "created_at": "2026-10-01T00:00:00",
                "reset_link_expires_at": None},
               {"id": 2, "first_name": "Mia", "last_name": "Two", "email": "m@example.com",
                "is_owner": False, "has_security_answer": False, "created_at": "2026-10-01T00:00:00",
                "reset_link_expires_at": None}]
    fake(monkeypatch, admin_handlers, "fetch_members", json=members)
    fake(monkeypatch, admin_handlers, "svc_reset_access", 201,
         {"token": "secret-token", "expires_at": "2026-11-01T10:00:00"})
    client = signed_in()

    listed = client.get("/admin/users")
    after = client.post("/admin/users/2/reset-access")

    assert "Reset access for Mia Two" in listed.text and "Reset access for Owner One" not in listed.text
    assert after.status_code == 200 and "/reset#secret-token" in after.text and "Link for Mia Two" in after.text
