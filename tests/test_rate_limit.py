"""Login and password reset are rate limited and do not reveal which emails exist."""
import uuid

from tests.helpers import PASSWORD, make_user

IP_A = {"CF-Connecting-IP": "203.0.113.10"}
IP_B = {"CF-Connecting-IP": "203.0.113.20"}


def _login(client, email, password, headers=None):
    return client.post("/api/auth/token",
                       data={"username": email, "password": password},
                       headers=headers)


def _reset(client, email, answer, headers=None):
    return client.post("/api/users/password/reset", headers=headers, json={
        "email": email, "security_answer": answer, "new_password": "newpass12345"})


def test_sixth_failed_login_for_one_email_is_blocked(client):
    _, email = make_user(client)

    codes = [_login(client, email, "wrong", IP_A).status_code for _ in range(5)]
    blocked = _login(client, email, "wrong", IP_A)

    assert codes == [401] * 5
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0
    # even the right password is refused while blocked from this address
    assert _login(client, email, PASSWORD, IP_A).status_code == 429


def test_block_does_not_lock_the_owner_out_from_another_address(client):
    _, email = make_user(client)
    for _ in range(6):
        _login(client, email, "wrong", IP_A)

    assert _login(client, email, PASSWORD, IP_B).status_code == 200


def test_successful_login_clears_the_failure_count(client):
    _, email = make_user(client)
    for _ in range(4):
        _login(client, email, "wrong", IP_A)
    assert _login(client, email, PASSWORD, IP_A).status_code == 200

    codes = [_login(client, email, "wrong", IP_A).status_code for _ in range(5)]

    assert codes == [401] * 5


def test_one_address_cannot_spray_many_emails(client):
    results = [
        _login(client, f"nobody_{uuid.uuid4().hex[:8]}@example.com", "x", IP_A).status_code
        for _ in range(31)
    ]

    assert results[:30] == [401] * 30
    assert results[30] == 429


def test_reset_gives_the_same_answer_for_every_kind_of_failure(client):
    _, known_email = make_user(client, answer="Rover")
    no_answer_headers, no_answer_email = make_user(client, answer="")

    unknown = _reset(client, f"nobody_{uuid.uuid4().hex[:8]}@example.com", "Rover")
    wrong = _reset(client, known_email, "Fido")
    unset = _reset(client, no_answer_email, "Rover")

    assert {unknown.status_code, wrong.status_code, unset.status_code} == {400}
    assert unknown.json() == wrong.json() == unset.json()


def test_reset_attempts_are_limited(client):
    _, email = make_user(client, answer="Rover")

    codes = [_reset(client, email, "Fido", IP_A).status_code for _ in range(5)]
    blocked = _reset(client, email, "Rover", IP_A)

    assert codes == [400] * 5
    assert blocked.status_code == 429


def test_web_layer_forwards_the_client_address_to_the_api(monkeypatch):
    """Without this the API would see its own address for every web login."""
    import asyncio
    from app.services import auth_service, user_service

    seen = []

    async def fake_post(path, json=None, data=None, headers=None, timeout=10.0):
        seen.append(headers)

    monkeypatch.setattr(auth_service, "post", fake_post)
    monkeypatch.setattr(user_service, "post", fake_post)

    asyncio.run(auth_service.login("a@example.com", "x", client_ip="203.0.113.7"))
    asyncio.run(user_service.reset_password("a@example.com", "x", "y", client_ip="203.0.113.7"))

    assert seen == [{"CF-Connecting-IP": "203.0.113.7"}] * 2
