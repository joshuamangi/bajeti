"""Default budget: the budget that opens after login."""
import httpx
from fastapi.testclient import TestClient

from app.handlers import auth_handlers
from app.handlers.dashboard_handlers import pick_budget_id
from main import app
from tests.helpers import first_budget_id, make_user


def new_budget(client, headers, name):
    return client.post("/api/budgets/", json={"name": name, "amount": 1000}, headers=headers).json()["id"]


def defaults(client, headers):
    return [b["id"] for b in client.get("/api/budgets/", headers=headers).json() if b["is_default"]]


def test_no_default_until_one_is_picked(client):
    headers, _ = make_user(client)
    assert defaults(client, headers) == []


def test_only_one_default_at_a_time(client):
    headers, _ = make_user(client)
    first = first_budget_id(client, headers)
    second = new_budget(client, headers, "Holiday")
    assert client.put(f"/api/budgets/{first}/default", headers=headers).json()["is_default"] is True
    client.put(f"/api/budgets/{second}/default", headers=headers)
    assert defaults(client, headers) == [second]


def test_clearing_the_default(client):
    headers, _ = make_user(client)
    first = first_budget_id(client, headers)
    client.put(f"/api/budgets/{first}/default", headers=headers)
    assert client.delete(f"/api/budgets/{first}/default", headers=headers).json()["is_default"] is False
    assert defaults(client, headers) == []


def test_other_user_gets_404(client):
    headers, _ = make_user(client)
    mine = first_budget_id(client, headers)
    other, _ = make_user(client)
    theirs = first_budget_id(client, other)
    client.put(f"/api/budgets/{theirs}/default", headers=other)
    assert client.put(f"/api/budgets/{mine}/default", headers=other).status_code == 404
    assert client.delete(f"/api/budgets/{mine}/default", headers=other).status_code == 404
    # A's budgets are untouched, and B's own default is not cleared by A's.
    assert defaults(client, headers) == []
    client.put(f"/api/budgets/{mine}/default", headers=headers)
    assert defaults(client, other) == [theirs]


BUDGETS = [{"id": 1}, {"id": 2, "is_default": True}, {"id": 3}]


def test_pick_order_link_then_cookie_then_default_then_first():
    assert pick_budget_id(BUDGETS, 3, "1") == 3
    assert pick_budget_id(BUDGETS, None, "1") == 1
    assert pick_budget_id(BUDGETS, None, None) == 2
    assert pick_budget_id([{"id": 1}, {"id": 3}], None, None) == 1


def test_pick_ignores_unknown_ids_and_bad_cookies():
    assert pick_budget_id(BUDGETS, 99, "98") == 2
    assert pick_budget_id(BUDGETS, None, "not-a-number") == 2


def test_login_clears_last_sessions_budget(monkeypatch):
    async def fake_login(*args, **kwargs):
        return httpx.Response(200, json={"access_token": "token-value"})
    monkeypatch.setattr(auth_handlers, "auth_login", fake_login)
    client = TestClient(app, follow_redirects=False)
    client.cookies.set("active_budget_id", "1")
    r = client.post("/login", data={"username": "demo@example.com", "password": "x"})
    cleared = [h for k, h in r.headers.multi_items() if k == "set-cookie" and h.startswith("active_budget_id=")]
    assert r.status_code == 303 and cleared and "Max-Age=0" in cleared[0]
