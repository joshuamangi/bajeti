"""Password change, security-answer protection and the owner's reset access links."""
from datetime import datetime, timedelta

from cli.set_owner import main as set_owner
from data.db.models.models import PasswordResetLink
from services.access_reset_service import AccessResetService
from tests.conftest import TestingSessionLocal
from tests.helpers import PASSWORD, make_user

NEW_PASSWORD = "brand-new-pass"


def _login(client, email, password):
    return client.post("/api/auth/token", data={"username": email, "password": password})


def _me(client, headers):
    return client.get("/api/auth/users/me", headers=headers)


def _make_owner(client, monkeypatch):
    monkeypatch.setattr("cli.set_owner.SessionLocal", TestingSessionLocal)
    headers, email = make_user(client)
    assert set_owner([email]) == 0
    return headers, email


def _reset(client, owner_headers, user_id):
    return client.post(f"/api/admin/users/{user_id}/reset-access", headers=owner_headers)


def _user_id(client, headers):
    return _me(client, headers).json()["id"]


# ---------- Change password ----------

def test_change_password_keeps_this_session_and_ends_others(client):
    headers, email = make_user(client)
    other_session = {"Authorization": f"Bearer {_login(client, email, PASSWORD).json()['access_token']}"}

    response = client.post("/api/users/me/password", headers=headers, json={
        "current_password": PASSWORD, "new_password": NEW_PASSWORD})

    assert response.status_code == 200
    new_headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    assert _me(client, new_headers).status_code == 200
    assert _me(client, headers).status_code == 401
    assert _me(client, other_session).status_code == 401
    assert _login(client, email, PASSWORD).status_code == 401
    assert _login(client, email, NEW_PASSWORD).status_code == 200


def test_change_password_with_wrong_current_password_changes_nothing(client):
    headers, email = make_user(client)

    response = client.post("/api/users/me/password", headers=headers, json={
        "current_password": "wrong-password", "new_password": NEW_PASSWORD})

    assert response.status_code == 400
    assert _me(client, headers).status_code == 200
    assert _login(client, email, PASSWORD).status_code == 200


def test_change_password_is_rate_limited(client):
    headers, _ = make_user(client)
    body = {"current_password": "wrong-password", "new_password": NEW_PASSWORD}
    codes = [client.post("/api/users/me/password", headers=headers, json=body).status_code
             for _ in range(6)]
    assert codes == [400] * 5 + [429]


def test_short_passwords_are_refused_everywhere(client):
    headers, email = make_user(client)
    assert client.post("/api/users/me/password", headers=headers, json={
        "current_password": PASSWORD, "new_password": "abc"}).status_code == 422
    assert client.post("/api/users/password/reset", json={
        "email": email, "security_answer": "TestAnswer", "new_password": "abc"}).status_code == 422
    assert client.post("/api/auth/", json={
        "first_name": "A", "last_name": "B", "email": "short@example.com",
        "password": "abc"}).status_code == 422


# ---------- Security answer needs the password ----------

def test_setting_security_answer_needs_current_password(client):
    headers, email = make_user(client, answer=None)

    missing = client.put("/api/users/me", headers=headers, json={"security_answer": "Rex"})
    wrong = client.put("/api/users/me", headers=headers, json={
        "security_answer": "Rex", "current_password": "wrong-password"})

    assert missing.status_code == 400 and wrong.status_code == 400
    assert _me(client, headers).json()["has_security_answer"] is False

    ok = client.put("/api/users/me", headers=headers, json={
        "security_answer": "Rex", "current_password": PASSWORD})
    assert ok.status_code == 200 and ok.json()["has_security_answer"] is True


def test_name_change_still_needs_no_password(client):
    headers, _ = make_user(client)
    response = client.put("/api/users/me", headers=headers, json={"first_name": "Renamed"})
    assert response.status_code == 200 and response.json()["first_name"] == "Renamed"


# ---------- Owner and Admin ----------

def test_set_owner_command(client, monkeypatch):
    headers, email = _make_owner(client, monkeypatch)
    assert _me(client, headers).json()["is_owner"] is True
    assert set_owner([email, "--remove"]) == 0
    assert _me(client, headers).json()["is_owner"] is False
    assert set_owner(["nobody@example.com"]) == 1


def test_members_get_404_on_admin(client, monkeypatch):
    _make_owner(client, monkeypatch)
    member, _ = make_user(client)
    other, _ = make_user(client)

    assert client.get("/api/admin/users", headers=member).status_code == 404
    assert _reset(client, member, _user_id(client, other)).status_code == 404
    assert _me(client, other).status_code == 200  # untouched


def test_owner_lists_members_without_secrets(client, monkeypatch):
    owner, _ = _make_owner(client, monkeypatch)
    make_user(client)

    members = client.get("/api/admin/users", headers=owner).json()

    assert members[0]["is_owner"] is True
    for m in members:
        assert "hashed_password" not in m and "security_answer" not in m


def test_owner_cannot_reset_themselves_or_unknown_users(client, monkeypatch):
    owner, _ = _make_owner(client, monkeypatch)
    assert _reset(client, owner, _user_id(client, owner)).status_code == 400
    assert _reset(client, owner, 999999).status_code == 404


def test_reset_access_end_to_end(client, monkeypatch):
    owner, _ = _make_owner(client, monkeypatch)
    member, email = make_user(client, answer=None)

    created = _reset(client, owner, _user_id(client, member))
    assert created.status_code == 201
    token = created.json()["token"]

    # The member is signed out everywhere and the old password still exists until they pick one.
    assert _me(client, member).status_code == 401

    used = client.post("/api/auth/reset-link", json={"token": token, "new_password": NEW_PASSWORD})
    assert used.status_code == 200
    assert _me(client, {"Authorization": f"Bearer {used.json()['access_token']}"}).status_code == 200
    assert _login(client, email, NEW_PASSWORD).status_code == 200

    # One use only.
    again = client.post("/api/auth/reset-link", json={"token": token, "new_password": "another-pass"})
    assert again.status_code == 400
    assert _login(client, email, NEW_PASSWORD).status_code == 200


def test_only_the_hash_of_the_token_is_stored(client, monkeypatch):
    owner, _ = _make_owner(client, monkeypatch)
    member, _ = make_user(client)
    token = _reset(client, owner, _user_id(client, member)).json()["token"]

    db = TestingSessionLocal()
    try:
        stored = [link.token_hash for link in db.query(PasswordResetLink).all()]
    finally:
        db.close()
    assert token not in stored
    assert AccessResetService.hash_token(token) in stored


def test_new_link_replaces_the_old_one(client, monkeypatch):
    owner, _ = _make_owner(client, monkeypatch)
    member, _ = make_user(client)
    member_id = _user_id(client, member)
    first = _reset(client, owner, member_id).json()["token"]
    second = _reset(client, owner, member_id).json()["token"]

    assert client.post("/api/auth/reset-link", json={
        "token": first, "new_password": NEW_PASSWORD}).status_code == 400
    assert client.post("/api/auth/reset-link", json={
        "token": second, "new_password": NEW_PASSWORD}).status_code == 200


def test_expired_link_fails(client, monkeypatch):
    owner, _ = _make_owner(client, monkeypatch)
    member, email = make_user(client)
    token = _reset(client, owner, _user_id(client, member)).json()["token"]

    db = TestingSessionLocal()
    try:
        link = db.query(PasswordResetLink).filter(
            PasswordResetLink.token_hash == AccessResetService.hash_token(token)).one()
        link.expires_at = datetime.utcnow() - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()

    assert client.post("/api/auth/reset-link", json={
        "token": token, "new_password": NEW_PASSWORD}).status_code == 400
    assert _login(client, email, NEW_PASSWORD).status_code == 401


def test_guessing_tokens_is_rate_limited(client):
    codes = [client.post("/api/auth/reset-link", json={
        "token": f"guess-{i}", "new_password": NEW_PASSWORD}).status_code
             for i in range(6)]
    assert codes == [400] * 5 + [429]


def test_owner_still_sees_link_until_used(client, monkeypatch):
    owner, _ = _make_owner(client, monkeypatch)
    member, _ = make_user(client)
    member_id = _user_id(client, member)
    _reset(client, owner, member_id)

    row = next(m for m in client.get("/api/admin/users", headers=owner).json() if m["id"] == member_id)
    assert row["reset_link_expires_at"] is not None

