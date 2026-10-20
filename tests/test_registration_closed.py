"""Registration is closed unless REGISTRATION_OPEN is turned on."""
import pytest

from app.config import settings

NEW_USER = {
    "first_name": "New", "last_name": "Person", "email": "new_person@example.com",
    "password": "testpass123", "security_answer": "Rover",
}


@pytest.fixture
def registration_closed(monkeypatch):
    monkeypatch.setattr(settings, "REGISTRATION_OPEN", False)


def test_default_is_closed():
    from app.config import Settings
    fields = Settings.model_fields
    assert fields["REGISTRATION_OPEN"].default is False


def test_api_register_is_404_when_closed(client, registration_closed):
    assert client.post("/api/auth/", json=NEW_USER).status_code == 404


def test_web_register_is_404_when_closed(client, registration_closed):
    assert client.get("/register").status_code == 404
    form = {"first_name": "N", "last_name": "P", "email": "n@example.com", "password": "x",
            "confirm_password": "x", "security_answer": "y"}
    assert client.post("/register", data=form).status_code == 404


def test_register_link_is_hidden_when_closed(client, registration_closed):
    assert 'href="/register"' not in client.get("/login").text


def test_register_works_when_open(client):
    assert client.post("/api/auth/", json={**NEW_USER, "email": "open_reg@example.com"}
                       ).status_code == 201
    assert client.get("/register").status_code == 200
    assert 'href="/register"' in client.get("/login").text


def test_existing_users_can_still_log_in_when_closed(client, registration_closed, monkeypatch):
    monkeypatch.setattr(settings, "REGISTRATION_OPEN", True)
    from tests.helpers import PASSWORD, make_user
    _, email = make_user(client)
    monkeypatch.setattr(settings, "REGISTRATION_OPEN", False)

    login = client.post("/api/auth/token", data={"username": email, "password": PASSWORD})

    assert login.status_code == 200
