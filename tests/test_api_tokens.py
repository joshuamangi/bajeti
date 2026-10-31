"""Phone tokens for the iPhone Shortcut: capture only, own inbox only. All data is made up."""
import hashlib

from core import rate_limit
from data.db.models.models import ApiToken
from tests.conftest import TestingSessionLocal
from tests.helpers import first_budget_id, make_user

PAID = "QAB12CD3EF Confirmed. Ksh450.00 paid to Demo Grocer on 26/10/26 at 12:38 PM. New M-PESA balance is Ksh9,050.00. Transaction cost, Ksh0.00."
SENT = "QAB12CD3EH Confirmed. Ksh300.00 sent to DEMO PERSON 0700000000 on 27/10/26 at 9:02 AM. Transaction cost, Ksh7.00."
RECEIVED = "QAB12CD3EQ Confirmed.You have received Ksh5,000.00 from DEMO PERSON 0744444444 on 27/10/26 at 1:00 PM."


def new_token(client, headers, name="iPhone"):
    r = client.post("/api/tokens/", json={"name": name}, headers=headers)
    assert r.status_code == 201
    return r.json()


def phone(token):
    return {"Authorization": f"Bearer {token}"}


def send(client, token, raw):
    return client.post("/api/payments/capture", json={"raw": raw, "source": "sms"}, headers=phone(token))


def test_token_is_shown_once_and_only_its_hash_is_stored(client):
    headers, _ = make_user(client)
    body = new_token(client, headers)
    assert body["token"].startswith("bjt_") and body["prefix"] == body["token"][:8]
    listed = client.get("/api/tokens/", headers=headers).json()
    assert [t["id"] for t in listed] == [body["id"]] and "token" not in listed[0]
    db = TestingSessionLocal()
    try:
        row = db.query(ApiToken).filter(ApiToken.id == body["id"]).one()
        assert row.token_hash == hashlib.sha256(body["token"].encode()).hexdigest()
        assert body["token"] not in (row.token_hash, row.prefix, row.name)
    finally:
        db.close()


def test_phone_token_captures_into_its_owners_inbox_with_a_message(client):
    headers, _ = make_user(client)
    token = new_token(client, headers)["token"]
    r = send(client, token, SENT)
    assert r.status_code == 201
    assert r.json()["message"] == "Added DEMO PERSON: Ksh 300.00 + 7.00 fee. Approve it in Bajeti."
    [p] = client.get("/api/payments/", headers=headers).json()["payments"]
    assert (p["source"], p["reference"]) == ("sms", "QAB12CD3EH")
    assert client.get("/api/tokens/", headers=headers).json()[0]["last_used_at"] is not None


def test_same_message_twice_from_the_phone_says_already_captured(client):
    headers, _ = make_user(client)
    token = new_token(client, headers)["token"]
    assert send(client, token, PAID).status_code == 201
    r = send(client, token, PAID)
    assert r.status_code == 409
    assert r.json()["message"].startswith("Already captured: QAB12CD3EF") and r.json()["detail"] == r.json()["message"]
    # Pasted in the app after the phone sent it: also refused.
    assert client.post("/api/payments/capture", json={"raw": PAID}, headers=headers).status_code == 409


def test_money_received_from_the_phone_explains_why_it_was_not_added(client):
    headers, _ = make_user(client)
    r = send(client, new_token(client, headers)["token"], RECEIVED)
    assert r.status_code == 200 and "received" in r.json()["message"]


def test_phone_token_cannot_be_used_anywhere_else(client):
    headers, _ = make_user(client)
    budget_id = first_budget_id(client, headers)
    token = new_token(client, headers)["token"]
    pid = send(client, token, PAID).json()["payment"]["id"]
    h = phone(token)
    assert client.get("/api/payments/", headers=h).status_code == 401
    assert client.get("/api/payments/count", headers=h).status_code == 401
    assert client.post(f"/api/payments/{pid}/dismiss", headers=h).status_code == 401
    assert client.get("/api/tokens/", headers=h).status_code == 401
    assert client.post("/api/tokens/", json={"name": "x"}, headers=h).status_code == 401
    assert client.get("/api/budgets/", headers=h).status_code == 401
    assert client.get(f"/api/budgets/{budget_id}", headers=h).status_code == 401
    assert client.get("/api/categories/", headers=h).status_code == 401
    assert client.put("/api/users/me", json={"first_name": "X"}, headers=h).status_code == 401


def test_revoked_or_unknown_token_is_refused(client):
    headers, _ = make_user(client)
    body = new_token(client, headers)
    assert client.delete(f"/api/tokens/{body['id']}", headers=headers).status_code == 204
    assert send(client, body["token"], PAID).status_code == 401
    assert send(client, "bjt_" + "x" * 43, PAID).status_code == 401
    assert client.get("/api/tokens/", headers=headers).json() == []


def test_too_many_bad_tokens_from_one_address_are_blocked(client):
    for _ in range(rate_limit.TOKEN_FAILS_PER_IP):
        assert send(client, "bjt_wrong", PAID).status_code == 401
    assert send(client, "bjt_wrong", PAID).status_code == 429


def test_one_phone_token_cannot_flood_the_inbox(client, monkeypatch):
    headers, _ = make_user(client)
    token = new_token(client, headers)["token"]
    limiter = rate_limit._capture_token
    monkeypatch.setattr(limiter, "max_failures", 2)
    assert send(client, token, PAID).status_code == 201
    assert send(client, token, SENT).status_code == 201
    assert send(client, token, RECEIVED).status_code == 429


def test_token_limit_per_user(client):
    headers, _ = make_user(client)
    for i in range(5):
        new_token(client, headers, f"Phone {i}")
    r = client.post("/api/tokens/", json={"name": "One more"}, headers=headers)
    assert r.status_code == 400 and "Revoke one first" in r.json()["detail"]


def test_second_user_cannot_see_or_revoke_tokens_or_messages(client):
    a, _ = make_user(client)
    b, _ = make_user(client)
    body = new_token(client, a)
    pid = send(client, body["token"], PAID).json()["payment"]["id"]
    assert client.get("/api/tokens/", headers=b).json() == []
    assert client.delete(f"/api/tokens/{body['id']}", headers=b).status_code == 404
    assert client.get("/api/payments/", headers=b).json()["payments"] == []
    assert client.post(f"/api/payments/{pid}/dismiss", headers=b).status_code == 404
    # A's token and message are untouched.
    assert [t["id"] for t in client.get("/api/tokens/", headers=a).json()] == [body["id"]]
    assert [p["id"] for p in client.get("/api/payments/", headers=a).json()["payments"]] == [pid]
    # B's own phone token puts the same message in B's inbox, not A's.
    assert send(client, new_token(client, b)["token"], PAID).status_code == 201
    assert len(client.get("/api/payments/", headers=a).json()["payments"]) == 1
