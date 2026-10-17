import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def make_user():
    """Create a user and return auth headers."""
    email = f"targets_{uuid.uuid4().hex[:10]}@example.com"
    client.post("/api/auth/", json={
        "first_name": "Target", "last_name": "Test", "email": email,
        "password": "testpass123", "security_answer": "TestAnswer"})
    token = client.post("/api/auth/token", data={
        "username": email, "password": "testpass123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def make_budget(headers, budget_type="expense"):
    response = client.post("/api/budgets/", headers=headers, json={
        "name": f"Budget {uuid.uuid4().hex[:6]}", "amount": 1000, "type": budget_type})
    assert response.status_code == 201, response.text
    return response.json()


def make_category(headers, category_type="expense"):
    response = client.post("/api/categories/", headers=headers, json={
        "name": f"Cat {uuid.uuid4().hex[:6]}", "type": category_type})
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def owner():
    headers = make_user()
    budget = make_budget(headers)
    category = make_category(headers)
    return {"headers": headers, "budget": budget, "category": category,
            "url": f"/api/budgets/{budget['id']}/targets/"}


def create_target(owner, **amounts):
    return client.post(owner["url"], headers=owner["headers"], json={
        "category_id": owner["category"]["id"], **amounts})


class TestTargets:
    def test_list_empty(self, owner):
        response = client.get(owner["url"], headers=owner["headers"])
        assert response.status_code == 200
        assert response.json() == []

    def test_create_target(self, owner):
        response = create_target(owner, short_term_amount="1234.56",
                                 mid_term_amount=5000, long_term_amount=20000)
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["budget_id"] == owner["budget"]["id"]
        assert data["category_id"] == owner["category"]["id"]
        assert data["category_name"] == owner["category"]["name"]
        assert Decimal(str(data["short_term_amount"])) == Decimal("1234.56")
        assert Decimal(str(data["long_term_amount"])) == Decimal("20000")

    def test_create_with_no_amounts(self, owner):
        response = create_target(owner)
        assert response.status_code == 201
        data = response.json()
        assert data["short_term_amount"] is None
        assert data["mid_term_amount"] is None
        assert data["long_term_amount"] is None

    def test_create_again_updates_existing_instead_of_conflict(self, owner):
        """The backfill migration creates empty targets, so POST on an existing pair updates it."""
        first = create_target(owner)
        second = create_target(owner, short_term_amount=300)
        assert first.status_code == 201
        assert second.status_code == 200
        assert second.json()["id"] == first.json()["id"]
        assert Decimal(str(second.json()["short_term_amount"])) == Decimal("300")
        listing = client.get(owner["url"], headers=owner["headers"]).json()
        assert len(listing) == 1

    def test_list_returns_created_targets(self, owner):
        create_target(owner, short_term_amount=10)
        listing = client.get(owner["url"], headers=owner["headers"]).json()
        assert len(listing) == 1
        assert listing[0]["category_name"] == owner["category"]["name"]

    def test_update_target(self, owner):
        target = create_target(owner, short_term_amount=10).json()
        response = client.put(f"{owner['url']}{target['id']}", headers=owner["headers"],
                              json={"mid_term_amount": 55})
        assert response.status_code == 200
        data = response.json()
        assert data["short_term_amount"] is None  # PUT replaces all three amounts
        assert Decimal(str(data["mid_term_amount"])) == Decimal("55")

    def test_delete_target(self, owner):
        target = create_target(owner, short_term_amount=10).json()
        url = f"{owner['url']}{target['id']}"
        assert client.delete(url, headers=owner["headers"]).status_code == 204
        assert client.get(owner["url"], headers=owner["headers"]).json() == []
        assert client.delete(url, headers=owner["headers"]).status_code == 404

    def test_negative_amount_rejected(self, owner):
        assert create_target(owner, short_term_amount=-1).status_code == 422
        target = create_target(owner).json()
        response = client.put(f"{owner['url']}{target['id']}", headers=owner["headers"],
                              json={"long_term_amount": -5})
        assert response.status_code == 422

    def test_category_type_must_match_budget_type(self, owner):
        savings_category = make_category(owner["headers"], "savings")
        response = client.post(owner["url"], headers=owner["headers"], json={
            "category_id": savings_category["id"], "short_term_amount": 1})
        assert response.status_code == 400

    def test_unknown_category_and_budget(self, owner):
        response = client.post(owner["url"], headers=owner["headers"],
                               json={"category_id": 999999})
        assert response.status_code == 404
        response = client.get("/api/budgets/999999/targets/", headers=owner["headers"])
        assert response.status_code == 404

    def test_unknown_target(self, owner):
        response = client.put(f"{owner['url']}999999", headers=owner["headers"], json={})
        assert response.status_code == 404


class TestTargetsAuth:
    def test_requires_authentication(self, owner):
        target = create_target(owner, short_term_amount=1).json()
        assert client.get(owner["url"]).status_code == 401
        assert client.post(owner["url"], json={"category_id": 1}).status_code == 401
        assert client.put(f"{owner['url']}{target['id']}", json={}).status_code == 401
        assert client.delete(f"{owner['url']}{target['id']}").status_code == 401


class TestTargetsCrossUser:
    """User B must not be able to read or change user A's targets."""

    def test_other_user_cannot_read_create_update_or_delete(self, owner):
        target = create_target(owner, short_term_amount=100).json()
        intruder = make_user()
        url = owner["url"]

        assert client.get(url, headers=intruder).status_code == 404
        assert client.post(url, headers=intruder, json={
            "category_id": owner["category"]["id"], "short_term_amount": 1}).status_code == 404
        assert client.put(f"{url}{target['id']}", headers=intruder,
                          json={"short_term_amount": 1}).status_code == 404
        assert client.delete(f"{url}{target['id']}", headers=intruder).status_code == 404

        # the owner's target is unchanged
        listing = client.get(url, headers=owner["headers"]).json()
        assert len(listing) == 1
        assert Decimal(str(listing[0]["short_term_amount"])) == Decimal("100")

    def test_other_user_cannot_use_someone_elses_category_on_their_own_budget(self, owner):
        intruder = make_user()
        own_budget = make_budget(intruder)
        response = client.post(f"/api/budgets/{own_budget['id']}/targets/", headers=intruder,
                               json={"category_id": owner["category"]["id"]})
        assert response.status_code == 404

    def test_target_id_from_another_budget_is_not_reachable(self, owner):
        """A target id must only work through the budget it belongs to."""
        target = create_target(owner, short_term_amount=5).json()
        other_budget = make_budget(owner["headers"])
        url = f"/api/budgets/{other_budget['id']}/targets/{target['id']}"
        assert client.put(url, headers=owner["headers"], json={}).status_code == 404
        assert client.delete(url, headers=owner["headers"]).status_code == 404
