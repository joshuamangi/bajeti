"""M-Pesa fees as their own expense, filing a captured payment as a recurring payment, and the usual
fee on recurring items (docs/design/payments.md). All messages are made up."""
from datetime import date
from decimal import Decimal

import pytest

from data.db.models.models import Allocation, Category, Expense, PendingPayment, RecurringExpense
from services import recurring_service
from tests.conftest import TestingSessionLocal
from tests.helpers import make_allocation, make_user

TODAY = date(2026, 10, 29)
# Paid on 27 Oct 2026, Ksh 300 + Ksh 7 fee.
SENT = "QAB12CD3EH Confirmed. Ksh300.00 sent to DEMO LANDLORD 0700000000 on 27/10/26 at 9:02 AM. Transaction cost, Ksh7.00."
SENT_AGAIN = SENT.replace("QAB12CD3EH", "QAB12CD3EX").replace("27/10/26", "28/10/26")
PAID_NO_FEE = "QAB12CD3EF Confirmed. Ksh450.00 paid to Demo Grocer on 26/10/26 at 12:38 PM. New M-PESA balance is Ksh9,050.00. Transaction cost, Ksh0.00."


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr(recurring_service, "today", lambda: TODAY)


def setup(client):
    headers, _ = make_user(client)
    budget_id, category_id, _ = make_allocation(client, headers, amount=6000.0)
    return headers, budget_id, category_id


def capture(client, headers, raw=SENT):
    r = client.post("/api/payments/capture", json={"raw": raw}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["payment"]["id"]


def item(client, headers, category_id, next_due, amount="300", mode="ask_first", name="Rent", usual_fee=None):
    body = {"name": name, "amount": amount, "category_id": category_id, "next_due": next_due.isoformat(), "mode": mode}
    if usual_fee is not None:
        body["usual_fee"] = usual_fee
    r = client.post("/api/recurring/", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def file(client, headers, pid, **body):
    return client.post(f"/api/payments/{pid}/recurring", json=body, headers=headers)


def amounts(category_id):
    """Expense amounts in a category, as Decimal strings, sorted."""
    db = TestingSessionLocal()
    try:
        return sorted(str(Decimal(str(e.amount)).quantize(Decimal("0.01")))
                      for e in db.query(Expense).filter(Expense.category_id == category_id))
    finally:
        db.close()


def fee_category(user_id):
    db = TestingSessionLocal()
    try:
        return db.query(Category).filter(Category.user_id == user_id, Category.name == "M-Pesa fees").all()
    finally:
        db.close()


def user_id_of(category_id):
    db = TestingSessionLocal()
    try:
        return db.query(Category).filter(Category.id == category_id).one().user_id
    finally:
        db.close()


def fee_category_id(category_id):
    [c] = fee_category(user_id_of(category_id))
    return c.id


def next_due(recurring_id):
    db = TestingSessionLocal()
    try:
        return db.query(RecurringExpense).filter(RecurringExpense.id == recurring_id).one().next_due
    finally:
        db.close()


class TestApprove:
    def test_fee_is_its_own_expense_in_m_pesa_fees(self, client):
        headers, budget_id, cat = setup(client)
        r = client.post(f"/api/payments/{capture(client, headers)}/approve", json={"category_id": cat}, headers=headers)
        assert r.status_code == 201
        assert (r.json()["amount"], r.json()["fee"]) == ("300.00", "7.00")
        fees = fee_category_id(cat)
        assert amounts(cat) == ["300.00"] and amounts(fees) == ["7.00"]
        db = TestingSessionLocal()
        try:
            [alloc] = db.query(Allocation).filter(Allocation.category_id == fees).all()
            assert (alloc.budget_id, float(alloc.allocated_amount)) == (budget_id, 0.0)
        finally:
            db.close()

    def test_the_fee_category_is_created_once_and_reused(self, client):
        headers, _, cat = setup(client)
        for raw in (SENT, SENT_AGAIN):
            client.post(f"/api/payments/{capture(client, headers, raw)}/approve", json={"category_id": cat}, headers=headers)
        assert len(fee_category(user_id_of(cat))) == 1
        assert amounts(fee_category_id(cat)) == ["7.00", "7.00"]

    def test_no_fee_means_one_expense_and_no_fee_category(self, client):
        headers, _, cat = setup(client)
        client.post(f"/api/payments/{capture(client, headers, PAID_NO_FEE)}/approve", json={"category_id": cat}, headers=headers)
        assert amounts(cat) == ["450.00"] and fee_category(user_id_of(cat)) == []

    def test_an_edited_amount_is_the_amount_before_the_fee(self, client):
        headers, _, cat = setup(client)
        client.post(f"/api/payments/{capture(client, headers)}/approve", json={"category_id": cat, "amount": "250"},
                    headers=headers)
        assert amounts(cat) == ["250.00"] and amounts(fee_category_id(cat)) == ["7.00"]

    def test_undo_removes_both_expenses(self, client):
        headers, _, cat = setup(client)
        pid = capture(client, headers)
        client.post(f"/api/payments/{pid}/approve", json={"category_id": cat}, headers=headers)
        fees = fee_category_id(cat)
        assert client.post(f"/api/payments/{pid}/restore", headers=headers).status_code == 204
        assert amounts(cat) == [] and amounts(fees) == []


class TestFileAsRecurring:
    def test_records_this_month_from_the_payment(self, client):
        headers, _, cat = setup(client)
        rec = item(client, headers, cat, date(2026, 10, 27), amount="280")
        r = file(client, headers, capture(client, headers), recurring_id=rec["id"])
        assert r.status_code == 201, r.text
        assert r.json()["message"] == "Recorded Rent for October 2026: Ksh 300.00 + Ksh 7.00 to M-Pesa fees."
        # The amount actually paid, not the budgeted 280; the item moves to November.
        assert amounts(cat) == ["300.00"] and amounts(fee_category_id(cat)) == ["7.00"]
        assert next_due(rec["id"]) == date(2026, 11, 27)
        assert client.get("/api/payments/count", headers=headers).json() == {"pending": 0}

    def test_already_recorded_adds_only_the_fee(self, client):
        headers, budget_id, cat = setup(client)
        rec = item(client, headers, cat, date(2026, 10, 5), amount="300", mode="auto")
        client.get(f"/api/recurring/?budget_id={budget_id}", headers=headers)  # records the auto item
        assert amounts(cat) == ["300.00"]
        r = file(client, headers, capture(client, headers), recurring_id=rec["id"])
        assert r.status_code == 201
        assert "already recorded, so only the fee was added" in r.json()["message"]
        assert amounts(cat) == ["300.00"] and amounts(fee_category_id(cat)) == ["7.00"]

    def test_already_recorded_with_a_different_amount_says_so(self, client):
        headers, budget_id, cat = setup(client)
        rec = item(client, headers, cat, date(2026, 10, 5), amount="320", mode="auto")
        client.get(f"/api/recurring/?budget_id={budget_id}", headers=headers)
        r = file(client, headers, capture(client, headers), recurring_id=rec["id"])
        assert "It was recorded as Ksh 320.00; this message says Ksh 300.00" in r.json()["message"]

    def test_the_real_fee_replaces_the_usual_fee_and_undo_puts_it_back(self, client):
        headers, budget_id, cat = setup(client)
        rec = item(client, headers, cat, date(2026, 10, 5), mode="auto", usual_fee="30")
        client.get(f"/api/recurring/?budget_id={budget_id}", headers=headers)
        fees = fee_category_id(cat)
        assert amounts(fees) == ["30.00"]
        pid = capture(client, headers)
        file(client, headers, pid, recurring_id=rec["id"])
        assert amounts(fees) == ["7.00"]
        client.post(f"/api/payments/{pid}/restore", headers=headers)
        assert amounts(fees) == ["30.00"] and amounts(cat) == ["300.00"]

    def test_an_earlier_month_still_due_is_refused(self, client):
        headers, _, cat = setup(client)
        rec = item(client, headers, cat, date(2026, 9, 27))
        r = file(client, headers, capture(client, headers), recurring_id=rec["id"])
        assert r.status_code == 409 and "still has September 2026 to record or skip" in r.json()["detail"]
        assert amounts(cat) == [] and client.get("/api/payments/count", headers=headers).json() == {"pending": 1}

    def test_a_skipped_month_is_refused(self, client):
        headers, _, cat = setup(client)
        rec = item(client, headers, cat, date(2026, 10, 27))
        client.post(f"/api/recurring/{rec['id']}/skip", json={"due_date": "2026-10-27"}, headers=headers)
        r = file(client, headers, capture(client, headers), recurring_id=rec["id"])
        assert r.status_code == 409 and "was skipped for October 2026" in r.json()["detail"]

    def test_an_item_that_starts_later_is_refused(self, client):
        headers, _, cat = setup(client)
        rec = item(client, headers, cat, date(2026, 11, 27))
        r = file(client, headers, capture(client, headers), recurring_id=rec["id"])
        assert r.status_code == 409 and "starts in November 2026" in r.json()["detail"]

    def test_new_item_from_the_payment(self, client):
        headers, _, cat = setup(client)
        r = file(client, headers, capture(client, headers), new={"name": "Rent", "category_id": cat, "mode": "auto"})
        assert r.status_code == 201, r.text
        rec = client.get("/api/recurring/", headers=headers).json()["items"]
        [made] = [i for i in rec if i["id"] == r.json()["recurring_id"]]
        assert (made["name"], made["amount"], made["anchor_day"], made["mode"], made["usual_fee"]) == \
            ("Rent", "300.00", 27, "auto", "7.00")
        assert made["next_due"] == "2026-11-27"
        assert amounts(cat) == ["300.00"] and amounts(fee_category_id(cat)) == ["7.00"]

    def test_undo_removes_the_run_and_makes_the_month_due_again(self, client):
        headers, _, cat = setup(client)
        rec = item(client, headers, cat, date(2026, 10, 27))
        pid = capture(client, headers)
        file(client, headers, pid, recurring_id=rec["id"])
        fees = fee_category_id(cat)
        assert client.post(f"/api/payments/{pid}/restore", headers=headers).status_code == 204
        assert amounts(cat) == [] and amounts(fees) == []
        assert next_due(rec["id"]) == date(2026, 10, 27)
        db = TestingSessionLocal()
        try:
            p = db.query(PendingPayment).filter(PendingPayment.id == pid).one()
            assert (p.status, p.recurring_run_id, p.fee_expense_id) == ("pending", None, None)
        finally:
            db.close()
        # It can be filed again.
        assert file(client, headers, pid, recurring_id=rec["id"]).status_code == 201

    def test_a_paused_item_is_refused(self, client):
        headers, _, cat = setup(client)
        rec = item(client, headers, cat, date(2026, 10, 27))
        client.post(f"/api/recurring/{rec['id']}/pause", headers=headers)
        r = file(client, headers, capture(client, headers), recurring_id=rec["id"])
        assert r.status_code == 409 and "paused" in r.json()["detail"]

    def test_choose_exactly_one_option(self, client):
        headers, _, cat = setup(client)
        pid = capture(client, headers)
        assert file(client, headers, pid).status_code == 422
        assert file(client, headers, pid, recurring_id=1, new={"name": "x", "category_id": cat}).status_code == 422


class TestSuggestions:
    def test_a_remembered_payee_suggests_its_item(self, client):
        headers, budget_id, cat = setup(client)
        rec = item(client, headers, cat, date(2026, 10, 27), amount="999")
        item(client, headers, cat, date(2026, 10, 27), amount="300", name="Other")
        file(client, headers, capture(client, headers), recurring_id=rec["id"], remember=True)
        capture(client, headers, SENT_AGAIN)
        inbox = client.get(f"/api/payments/?budget_id={budget_id}", headers=headers).json()
        [p] = inbox["payments"]
        assert p["suggested_recurring_id"] == rec["id"]
        assert {r["name"] for r in inbox["recurring"]} == {"Rent", "Other"}

    def test_the_one_item_with_the_same_amount_is_suggested(self, client):
        headers, budget_id, cat = setup(client)
        rec = item(client, headers, cat, date(2026, 10, 27), amount="300")
        item(client, headers, cat, date(2026, 10, 27), amount="450", name="Water")
        capture(client, headers)
        [p] = client.get(f"/api/payments/?budget_id={budget_id}", headers=headers).json()["payments"]
        assert p["suggested_recurring_id"] == rec["id"]


class TestUsualFee:
    def test_recording_adds_the_usual_fee_and_undo_removes_it(self, client):
        headers, _, cat = setup(client)
        rec = item(client, headers, cat, date(2026, 10, 1), usual_fee="30")
        r = client.post(f"/api/recurring/{rec['id']}/approve", json={"due_date": "2026-10-01"}, headers=headers)
        assert r.status_code == 201
        fees = fee_category_id(cat)
        assert amounts(cat) == ["300.00"] and amounts(fees) == ["30.00"]
        assert client.delete(f"/api/recurring/{rec['id']}/runs/2026-10-01", headers=headers).status_code == 204
        assert amounts(cat) == [] and amounts(fees) == []

    def test_no_usual_fee_adds_nothing(self, client):
        headers, _, cat = setup(client)
        rec = item(client, headers, cat, date(2026, 10, 1))
        client.post(f"/api/recurring/{rec['id']}/approve", json={"due_date": "2026-10-01"}, headers=headers)
        assert amounts(cat) == ["300.00"] and fee_category(user_id_of(cat)) == []

    def test_usual_fee_is_saved_and_returned(self, client):
        headers, _, cat = setup(client)
        rec = item(client, headers, cat, date(2026, 11, 1), usual_fee="33")
        assert rec["usual_fee"] == "33.00"


class TestOtherUsers:
    def test_second_user_cannot_file_or_use_the_first_users_things(self, client):
        a, _, cat_a = setup(client)
        b, _, cat_b = setup(client)
        rec_a = item(client, a, cat_a, date(2026, 10, 27))
        pid_a = capture(client, a)
        # B cannot file A's payment.
        assert file(client, b, pid_a, recurring_id=rec_a["id"]).status_code == 404
        pid_b = capture(client, b)
        # B cannot file into A's recurring item or create an item in A's category.
        assert file(client, b, pid_b, recurring_id=rec_a["id"]).status_code == 404
        assert file(client, b, pid_b, new={"name": "Rent", "category_id": cat_a}).status_code == 404
        # A's data is untouched.
        assert amounts(cat_a) == [] and next_due(rec_a["id"]) == date(2026, 10, 27)
        assert client.get("/api/payments/count", headers=a).json() == {"pending": 1}
