from decimal import Decimal

from sqlalchemy import event

from tests.conftest import engine
from tests.helpers import first_budget_id, make_allocation, make_user


def _stats(client, headers, budget_id):
    response = client.get(f"/api/categories/with-stats/{budget_id}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _set_target(client, headers, budget_id, category_id, **amounts):
    response = client.post(
        f"/api/budgets/{budget_id}/targets/",
        json={"category_id": category_id, **amounts},
        headers=headers,
    )
    assert response.status_code in (200, 201), response.text


def test_category_without_target_has_none(client):
    headers, _ = make_user(client)
    budget_id, category_id, _ = make_allocation(client, headers, amount=100.0)

    rows = _stats(client, headers, budget_id)

    assert [r["id"] for r in rows] == [category_id]
    assert rows[0]["target"] is None


def test_progress_per_horizon(client):
    headers, _ = make_user(client)
    budget_id, category_id, _ = make_allocation(client, headers, amount=100.0)
    _set_target(client, headers, budget_id, category_id,
                short_term_amount="200", mid_term_amount="400")

    target = _stats(client, headers, budget_id)[0]["target"]

    assert target["short_term"] == {"amount": "200.00", "percent": 50.0, "remaining": "100.00"}
    assert target["mid_term"] == {"amount": "400.00", "percent": 25.0, "remaining": "300.00"}
    assert target["long_term"] is None


def test_backfilled_empty_target_has_no_horizons(client):
    headers, _ = make_user(client)
    budget_id, category_id, _ = make_allocation(client, headers, amount=100.0)
    _set_target(client, headers, budget_id, category_id)

    target = _stats(client, headers, budget_id)[0]["target"]

    assert target["short_term"] is None and target["mid_term"] is None and target["long_term"] is None


def test_reached_target_shows_over_100_and_nothing_remaining(client):
    headers, _ = make_user(client)
    budget_id, category_id, _ = make_allocation(client, headers, amount=300.0)
    _set_target(client, headers, budget_id, category_id, short_term_amount="200")

    short = _stats(client, headers, budget_id)[0]["target"]["short_term"]

    assert short["percent"] == 150.0
    assert Decimal(short["remaining"]) == Decimal("0")


def test_other_user_gets_no_stats_or_targets(client):
    headers_a, _ = make_user(client)
    headers_b, _ = make_user(client)
    budget_id, category_id, _ = make_allocation(client, headers_a, amount=100.0)
    _set_target(client, headers_a, budget_id, category_id, short_term_amount="200")

    assert _stats(client, headers_b, budget_id) == []
    assert len(_stats(client, headers_a, budget_id)) == 1


def test_targets_are_loaded_in_one_query_however_many_categories(client):
    headers, _ = make_user(client)
    budget_id, first_category, _ = make_allocation(client, headers, amount=100.0)
    _set_target(client, headers, budget_id, first_category, short_term_amount="200")

    def target_queries():
        seen = []

        def record(conn, cursor, statement, *args):
            if "FROM targets" in statement:
                seen.append(statement)

        event.listen(engine, "before_cursor_execute", record)
        try:
            _stats(client, headers, budget_id)
        finally:
            event.remove(engine, "before_cursor_execute", record)
        return len(seen)

    one_category = target_queries()
    for _ in range(3):
        _, category_id, _ = make_allocation(client, headers, amount=50.0)
        _set_target(client, headers, first_budget_id(client, headers), category_id,
                    short_term_amount="100")

    assert one_category == 1
    assert target_queries() == 1
