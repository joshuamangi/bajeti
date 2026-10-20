"""Shared helpers for tests that need more than one user.

Cross-user pattern for every new endpoint: create user A with data, create user B,
then check that B gets 404 on A's resources and that A's data is unchanged.
"""
import uuid

PASSWORD = "testpass123"


def make_user(client, answer="TestAnswer"):
    """Register a user with a unique email, log in, return (headers, email)."""
    email = f"user_{uuid.uuid4().hex[:10]}@example.com"
    client.post("/api/auth/", json={
        "first_name": "Test",
        "last_name": "User",
        "email": email,
        "password": PASSWORD,
        "security_answer": answer,
    })
    token = client.post(
        "/api/auth/token", data={"username": email, "password": PASSWORD}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, email


def first_budget_id(client, headers):
    """Id of the default budget created at registration."""
    return client.get("/api/budgets/", headers=headers).json()[0]["id"]


def make_allocation(client, headers, amount=100.0):
    """Create a category and an allocation in the user's default budget.

    Returns (budget_id, category_id, allocation_id).
    """
    budget_id = first_budget_id(client, headers)
    category = client.post(
        "/api/categories/",
        json={"name": f"Cat {uuid.uuid4().hex[:6]}"},
        headers=headers,
    ).json()
    allocation = client.post(
        f"/api/budgets/{budget_id}/allocations/",
        json={"category_id": category["id"], "allocated_amount": amount},
        headers=headers,
    ).json()
    return budget_id, category["id"], allocation["id"]
