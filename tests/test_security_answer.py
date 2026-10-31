"""Security answers are stored hashed and never sent back to the client."""
import importlib

from passlib.context import CryptContext

from data.db.models.models import User
from tests.conftest import TestingSessionLocal
from tests.helpers import PASSWORD, make_user

pwd_context = CryptContext(schemes=["bcrypt"])


def _stored_answer(email):
    db = TestingSessionLocal()
    try:
        return db.query(User).filter(User.email == email).one().security_answer
    finally:
        db.close()


def _reset(client, email, answer, new_password="newpass12345"):
    return client.post("/api/users/password/reset", json={
        "email": email, "security_answer": answer, "new_password": new_password})


def test_answer_is_stored_hashed_at_registration(client):
    _, email = make_user(client, answer="Rover")

    stored = _stored_answer(email)

    assert stored != "Rover"
    assert pwd_context.verify("rover", stored)


def test_answer_is_stored_hashed_after_profile_update(client):
    headers, email = make_user(client)

    client.put("/api/users/me", json={"security_answer": "Fluffy", "current_password": PASSWORD},
               headers=headers)

    stored = _stored_answer(email)
    assert stored != "Fluffy"
    assert pwd_context.verify("fluffy", stored)


def test_reset_ignores_case_and_surrounding_spaces(client):
    _, email = make_user(client, answer="Rover")

    response = _reset(client, email, "  ROVER ")

    assert response.status_code == 200
    login = client.post("/api/auth/token",
                        data={"username": email, "password": "newpass12345"})
    assert login.status_code == 200


def test_reset_with_wrong_answer_changes_nothing(client):
    _, email = make_user(client, answer="Rover")

    response = _reset(client, email, "Fido")

    assert response.status_code == 400
    login = client.post("/api/auth/token",
                        data={"username": email, "password": PASSWORD})
    assert login.status_code == 200


def test_answer_is_not_returned_by_the_api(client):
    headers, _ = make_user(client, answer="Rover")

    me = client.get("/api/auth/users/me", headers=headers).json()
    updated = client.put("/api/users/me", json={"first_name": "X"},
                         headers=headers).json()

    for body in (me, updated):
        assert "security_answer" not in body
        assert body["has_security_answer"] is True


def test_migration_rehashes_plain_values_and_is_safe_to_rerun():
    migration = importlib.import_module(
        "migrations.versions.b7c1d2e3f4a5_hash_security_answers")
    already_hashed = pwd_context.hash("kept")

    assert migration.rehash("  Rover ") != "  Rover "
    assert pwd_context.verify("rover", migration.rehash("  Rover "))
    assert migration.rehash(already_hashed) == already_hashed
    assert migration.rehash(None) is None
    assert migration.rehash("") == ""
