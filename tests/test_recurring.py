from datetime import date, timedelta

import pytest

from services import recurring_service
from services.recurring_service import due_dates, month_day, next_month
from tests.helpers import make_allocation, make_user

TODAY = date(2026, 10, 29)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr(recurring_service, "today", lambda: TODAY)


class TestDates:
    def test_day_31_uses_the_last_day_of_shorter_months(self):
        d = date(2026, 1, 31)
        seen = []
        for _ in range(4):
            seen.append(d)
            d = next_month(d, 31)
        assert seen == [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 30)]

    def test_leap_year_february(self):
        assert month_day(2028, 2, 30) == date(2028, 2, 29)

    def test_year_end(self):
        assert next_month(date(2026, 12, 15), 15) == date(2027, 1, 15)

    def test_due_dates_up_to_today(self):
        assert due_dates(date(2026, 8, 1), 1, TODAY) == [date(2026, 8, 1), date(2026, 9, 1), date(2026, 10, 1)]
        assert due_dates(date(2026, 11, 1), 1, TODAY) == []

    def test_today_is_nairobi_time(self, monkeypatch):
        monkeypatch.undo()  # the real today()
        from datetime import datetime, timezone
        expected = (datetime.now(timezone.utc) + timedelta(hours=3)).date()
        assert recurring_service.today() == expected


def item(client, headers, category_id, next_due, amount="3500", mode="ask_first", name="Internet"):
    r = client.post("/api/recurring/", json={"name": name, "amount": amount, "category_id": category_id,
                                             "next_due": next_due.isoformat(), "mode": mode}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def expenses(client, headers, category_id):
    r = client.get(f"/api/expenses/category/{category_id}", headers=headers)
    return [] if r.status_code == 404 else r.json()  # the endpoint answers 404 when there are none


def setup(client):
    headers, _ = make_user(client)
    budget_id, category_id, _ = make_allocation(client, headers, amount=6000.0)
    return headers, budget_id, category_id


def test_due_now_shows_on_the_due_date_not_before(client):
    headers, budget_id, cat = setup(client)
    item(client, headers, cat, TODAY, name="Today")
    item(client, headers, cat, TODAY + timedelta(days=1), name="Tomorrow")
    due = client.get(f"/api/recurring/due?budget_id={budget_id}", headers=headers).json()
    assert [d["name"] for d in due] == ["Today"]
    assert due[0]["days"] == 0 and due[0]["overdue"] == 1


def test_approve_records_the_expense_in_the_due_month_and_moves_on(client):
    headers, budget_id, cat = setup(client)
    rec = item(client, headers, cat, date(2026, 9, 30))
    r = client.post(f"/api/recurring/{rec['id']}/approve", json={"due_date": "2026-09-30"}, headers=headers)
    assert r.status_code == 201, r.text
    [e] = expenses(client, headers, cat)
    assert (e["month"], e["description"], float(e["amount"])) == ("2026-09", "Internet", 3500.0)
    listing = client.get(f"/api/recurring/?budget_id={budget_id}", headers=headers).json()
    assert listing["items"][0]["next_due"] == "2026-10-30"
    # 30 Oct is tomorrow, so it is not in Due now yet.
    assert client.get(f"/api/recurring/due?budget_id={budget_id}", headers=headers).json() == []


def test_approving_twice_records_one_expense(client):
    headers, _, cat = setup(client)
    rec = item(client, headers, cat, date(2026, 10, 28))
    url = f"/api/recurring/{rec['id']}/approve"
    assert client.post(url, json={"due_date": "2026-10-28"}, headers=headers).status_code == 201
    second = client.post(url, json={"due_date": "2026-10-28"}, headers=headers)
    assert second.status_code == 409 and second.json()["detail"] == "Already recorded"
    assert len(expenses(client, headers, cat)) == 1


def test_catch_up_one_card_with_overdue_count_and_approve_all(client):
    headers, budget_id, cat = setup(client)
    rec = item(client, headers, cat, date(2026, 8, 31))
    due = client.get(f"/api/recurring/due?budget_id={budget_id}", headers=headers).json()
    assert len(due) == 1 and due[0]["overdue"] == 2   # 31 Aug and 30 Sep; 31 Oct is still ahead
    assert due[0]["due_date"] == "2026-08-31"
    r = client.post(f"/api/recurring/{rec['id']}/approve-all", headers=headers)
    assert r.json() == {"recorded": 2}  # 31 Aug and 30 Sep; 31 Oct is still ahead
    assert sorted(e["month"] for e in expenses(client, headers, cat)) == ["2026-08", "2026-09"]


def test_skip_records_nothing_and_undo_brings_it_back(client):
    headers, budget_id, cat = setup(client)
    rec = item(client, headers, cat, date(2026, 10, 28))
    client.post(f"/api/recurring/{rec['id']}/skip", json={"due_date": "2026-10-28"}, headers=headers)
    assert expenses(client, headers, cat) == []
    assert client.get(f"/api/recurring/due?budget_id={budget_id}", headers=headers).json() == []
    assert client.delete(f"/api/recurring/{rec['id']}/runs/2026-10-28", headers=headers).status_code == 204
    assert client.get(f"/api/recurring/due?budget_id={budget_id}", headers=headers).json()[0]["due_date"] == "2026-10-28"


def test_undo_an_approval_deletes_its_expense(client):
    headers, _, cat = setup(client)
    rec = item(client, headers, cat, date(2026, 10, 28))
    client.post(f"/api/recurring/{rec['id']}/approve", json={"due_date": "2026-10-28"}, headers=headers)
    client.delete(f"/api/recurring/{rec['id']}/runs/2026-10-28", headers=headers)
    assert expenses(client, headers, cat) == []


def test_changing_the_amount_keeps_past_expenses(client):
    headers, _, cat = setup(client)
    rec = item(client, headers, cat, date(2026, 10, 28))
    client.post(f"/api/recurring/{rec['id']}/approve", json={"due_date": "2026-10-28"}, headers=headers)
    r = client.put(f"/api/recurring/{rec['id']}", json={"name": "Internet", "amount": "4000", "category_id": cat,
                                                      "next_due": "2026-11-28", "mode": "ask_first"}, headers=headers)
    assert r.status_code == 200 and r.json()["amount"] == "4000.00"
    assert [float(e["amount"]) for e in expenses(client, headers, cat)] == [3500.0]


def test_auto_items_are_added_when_the_page_loads(client):
    headers, budget_id, cat = setup(client)
    item(client, headers, cat, date(2026, 9, 5), mode="auto", name="Gym")
    listing = client.get(f"/api/recurring/?budget_id={budget_id}", headers=headers).json()
    assert sorted(e["month"] for e in expenses(client, headers, cat)) == ["2026-09", "2026-10"]
    assert [r["action"] for r in listing["recent"]] == ["auto", "auto"]
    assert listing["items"][0]["next_due"] == "2026-11-05"
    # A second load adds nothing more.
    client.get(f"/api/recurring/due?budget_id={budget_id}", headers=headers)
    assert len(expenses(client, headers, cat)) == 2


def test_paused_items_are_never_due_or_added(client):
    headers, budget_id, cat = setup(client)
    rec = item(client, headers, cat, date(2026, 10, 1), mode="auto")
    client.post(f"/api/recurring/{rec['id']}/pause", headers=headers)
    client.get(f"/api/recurring/due?budget_id={budget_id}", headers=headers)
    assert expenses(client, headers, cat) == []
    listing = client.get(f"/api/recurring/?budget_id={budget_id}", headers=headers).json()
    assert listing["active_count"] == 0 and listing["items"][0]["paused"] is True


def test_monthly_total(client):
    headers, budget_id, cat = setup(client)
    item(client, headers, cat, date(2026, 11, 1), amount="3500")
    item(client, headers, cat, date(2026, 11, 5), amount="2500", name="Gym")
    listing = client.get(f"/api/recurring/?budget_id={budget_id}", headers=headers).json()
    assert (listing["monthly_total"], listing["active_count"]) == ("6000.00", 2)


def test_savings_categories_are_refused(client):
    headers, _ = make_user(client)
    cat = client.post("/api/categories/", json={"name": "Holiday", "type": "savings"}, headers=headers).json()
    r = client.post("/api/recurring/", json={"name": "Save", "amount": "100", "category_id": cat["id"],
                                             "next_due": "2026-11-01"}, headers=headers)
    assert r.status_code == 400


def test_deleting_a_category_with_recurring_items_is_refused(client):
    headers, _, cat = setup(client)
    item(client, headers, cat, date(2026, 11, 1))
    r = client.delete(f"/api/categories/{cat}", headers=headers)
    assert r.status_code == 409 and "1 recurring item" in r.json()["detail"]


def test_other_user_gets_404_everywhere(client):
    headers, budget_id, cat = setup(client)
    rec = item(client, headers, cat, date(2026, 10, 28))
    other, _ = make_user(client)
    rid = rec["id"]
    body = {"name": "x", "amount": "1", "category_id": cat, "next_due": "2026-11-01", "mode": "ask_first"}
    calls = [
        ("get", f"/api/recurring/?budget_id={budget_id}", None),
        ("get", f"/api/recurring/due?budget_id={budget_id}", None),
        ("put", f"/api/recurring/{rid}", body),
        ("post", f"/api/recurring/{rid}/pause", None),
        ("post", f"/api/recurring/{rid}/resume", None),
        ("post", f"/api/recurring/{rid}/approve", {"due_date": "2026-10-28"}),
        ("post", f"/api/recurring/{rid}/skip", {"due_date": "2026-10-28"}),
        ("post", f"/api/recurring/{rid}/approve-all", None),
        ("delete", f"/api/recurring/{rid}/runs/2026-10-28", None),
        ("delete", f"/api/recurring/{rid}", None),
        ("post", "/api/recurring/", body),   # someone else's category
    ]
    for method, url, json in calls:
        r = getattr(client, method)(url, json=json, headers=other) if json else getattr(client, method)(url, headers=other)
        assert r.status_code == 404, (method, url, r.status_code)
    # The owner's item and data are unchanged.
    assert client.get(f"/api/recurring/due?budget_id={budget_id}", headers=headers).json()[0]["id"] == rid
    assert expenses(client, headers, cat) == []


def test_two_tabs_approving_at_once_record_one_expense(client):
    """The other tab already wrote the run, but this tab still sees the item as due."""
    from data.db.models.models import RecurringRun
    from tests.conftest import TestingSessionLocal
    headers, _, cat = setup(client)
    rec = item(client, headers, cat, date(2026, 10, 28))
    db = TestingSessionLocal()
    user_id = db.execute(__import__("sqlalchemy").text(
        "select user_id from recurring_expenses where id = :i"), {"i": rec["id"]}).scalar()
    db.add(RecurringRun(recurring_id=rec["id"], user_id=user_id, due_date=date(2026, 10, 28), action="skipped"))
    db.commit()
    db.close()
    r = client.post(f"/api/recurring/{rec['id']}/approve", json={"due_date": "2026-10-28"}, headers=headers)
    assert r.status_code == 409
    assert expenses(client, headers, cat) == []
