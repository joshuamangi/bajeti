"""Cross-user checks for the allocation endpoints."""
from tests.helpers import make_allocation, make_user


def _overview(client, headers, budget_id):
    return client.get(
        f"/api/budgets/{budget_id}/allocations/overview", headers=headers
    ).json()["allocations"]


def test_other_user_cannot_update_allocation(client):
    headers_a, _ = make_user(client)
    headers_b, _ = make_user(client)
    budget_id, category_id, _ = make_allocation(client, headers_a, amount=100.0)

    response = client.put(
        f"/api/budgets/{budget_id}/allocations/",
        json={"category_id": category_id, "allocated_amount": 999.0},
        headers=headers_b,
    )

    assert response.status_code == 404
    rows = _overview(client, headers_a, budget_id)
    assert [r["allocated_amount"] for r in rows] == [100.0]


def test_other_user_cannot_delete_allocation(client):
    headers_a, _ = make_user(client)
    headers_b, _ = make_user(client)
    budget_id, _, allocation_id = make_allocation(client, headers_a)

    response = client.delete(
        f"/api/budgets/{budget_id}/allocations/{allocation_id}",
        headers=headers_b,
    )

    assert response.status_code == 404
    assert len(_overview(client, headers_a, budget_id)) == 1


def test_owner_can_update_and_delete_allocation(client):
    headers, _ = make_user(client)
    budget_id, category_id, allocation_id = make_allocation(client, headers)

    updated = client.put(
        f"/api/budgets/{budget_id}/allocations/",
        json={"category_id": category_id, "allocated_amount": 250.0},
        headers=headers,
    )
    assert updated.status_code == 200
    assert _overview(client, headers, budget_id)[0]["allocated_amount"] == 250.0

    deleted = client.delete(
        f"/api/budgets/{budget_id}/allocations/{allocation_id}",
        headers=headers,
    )
    assert deleted.status_code == 204
    assert _overview(client, headers, budget_id) == []
