"""Bank messages filed to savings (docs/design/payments.md): money from a bank to M-Pesa and card
purchases are withdrawals from a savings category, a bank deposit adds to a savings budget.
All messages, banks, card and account numbers are made up."""
import uuid
from datetime import date
from decimal import Decimal

import pytest

from data.db.models.models import Allocation, Budget, Expense
from services.payment_parser import parse
from tests.conftest import TestingSessionLocal
from tests.helpers import make_user

RECEIVED = ("QAB12CD3EB Confirmed.You have received Ksh2,000.00 from B2C Demo Bank 000111 on 30/10/26 at 11:03 PM "
            "New M-PESA balance is Ksh5,000.00. See all your balances now https://example.com/x")
CARD = ("Dear Client, a transaction of KES 1500.00 was made on card ending 0001 at Demo Motors Limited on 2026-10-29. "
        "For any queries call +254 20 0000000")
DEPOSIT = "Dear Client, KES 10000.00 was deposited to Acc. ending with 0002. For any queries call +254 20 0000000"
FROM_PERSON = ("QAB12CD3EQ Confirmed.You have received Ksh5,000.00 from DEMO PERSON 0744444444 on 27/10/26 "
               "at 1:00 PM New M-PESA balance is Ksh10,000.00.")


@pytest.mark.parametrize("message, kind, amount, payee, account, reference, paid_on", [
    (RECEIVED, "received", "2000.00", "Demo Bank 000111", None, "QAB12CD3EB", date(2026, 10, 30)),
    (CARD, "card", "1500.00", "Demo Motors Limited", "Card ending 0001", None, date(2026, 10, 29)),
    (DEPOSIT, "deposit", "10000.00", None, "Acc. ending 0002", None, None),
])
def test_bank_messages_are_read(message, kind, amount, payee, account, reference, paid_on):
    p = parse(message)
    assert (p["kind"], p["amount"], p["payee"], p["account"], p["reference"], p["paid_on"]) == \
        (kind, Decimal(amount), payee, account, reference, paid_on)
    assert p["fee"] is None


def test_money_from_a_person_is_still_ignored():
    assert parse(FROM_PERSON)["ignored"]


def make_budget(client, headers, amount=5000, budget_type="savings"):
    r = client.post("/api/budgets/", headers=headers, json={
        "name": f"Savings {uuid.uuid4().hex[:6]}", "amount": amount, "type": budget_type})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def savings_setup(client, budget_amount=5000, allocated=3000):
    """A user with a savings budget and one savings category allocated in it."""
    headers, _ = make_user(client)
    budget_id = make_budget(client, headers, budget_amount)
    c = client.post("/api/categories/", json={"name": f"Emergency {uuid.uuid4().hex[:4]}", "type": "savings"},
                    headers=headers).json()
    r = client.post(f"/api/budgets/{budget_id}/allocations/", json={"category_id": c["id"], "allocated_amount": allocated},
                    headers=headers)
    assert r.status_code in (200, 201), r.text
    return headers, budget_id, c["id"]


def capture(client, headers, raw):
    r = client.post("/api/payments/capture", json={"raw": raw, "source": "sms"}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def balances(budget_id, category_id=None):
    db = TestingSessionLocal()
    try:
        budget = Decimal(str(db.query(Budget).filter(Budget.id == budget_id).one().amount))
        if category_id is None:
            return budget
        allocated = Decimal(str(db.query(Allocation).filter(Allocation.category_id == category_id).one().allocated_amount))
        return budget, allocated
    finally:
        db.close()


def withdrawals(category_id):
    db = TestingSessionLocal()
    try:
        return [(Decimal(str(e.amount)), e.description, e.month)
                for e in db.query(Expense).filter(Expense.category_id == category_id, Expense.type == "withdrawal")]
    finally:
        db.close()


@pytest.mark.parametrize("message, description, month", [
    (RECEIVED, "Demo Bank 000111", "2026-10"),
    (CARD, "Demo Motors Limited", "2026-10"),
])
def test_withdrawal_lowers_budget_and_allocation_and_undo_puts_it_back(client, message, description, month):
    headers, budget_id, category_id = savings_setup(client)
    body = capture(client, headers, message)
    assert body["payment"]["savings"] == "withdrawal"
    assert "Approve it in Bajeti" in body["message"]
    pid = body["payment"]["id"]
    amount = body["payment"]["amount"]

    r = client.post(f"/api/payments/{pid}/savings", json={"category_id": category_id}, headers=headers)
    assert r.status_code == 201, r.text
    assert balances(budget_id, category_id) == (Decimal("5000") - Decimal(amount), Decimal("3000") - Decimal(amount))
    assert withdrawals(category_id) == [(Decimal(amount), description, month)]

    assert client.post(f"/api/payments/{pid}/restore", headers=headers).status_code == 204
    assert balances(budget_id, category_id) == (Decimal("5000"), Decimal("3000"))
    assert withdrawals(category_id) == []
    assert client.get("/api/payments/count", headers=headers).json() == {"pending": 1}


def test_withdrawal_larger_than_the_allocation_is_refused(client):
    headers, budget_id, category_id = savings_setup(client, allocated=1000)
    pid = capture(client, headers, CARD)["payment"]["id"]
    r = client.post(f"/api/payments/{pid}/savings", json={"category_id": category_id}, headers=headers)
    assert r.status_code == 400 and "has only" in r.json()["detail"]
    assert balances(budget_id, category_id) == (Decimal("5000"), Decimal("1000"))


def test_withdrawal_needs_a_savings_category(client):
    headers, _, _ = savings_setup(client)
    expense = client.post("/api/categories/", json={"name": "Groceries"}, headers=headers).json()
    pid = capture(client, headers, CARD)["payment"]["id"]
    r = client.post(f"/api/payments/{pid}/savings", json={"category_id": expense["id"]}, headers=headers)
    assert r.status_code == 400


def test_deposit_raises_the_budget_amount_and_undo_takes_it_off(client):
    headers, budget_id, category_id = savings_setup(client)
    body = capture(client, headers, DEPOSIT)
    assert body["payment"]["savings"] == "deposit"
    assert body["message"].startswith("Added deposit to Acc. ending 0002")
    pid = body["payment"]["id"]

    r = client.post(f"/api/payments/{pid}/savings", json={"budget_id": budget_id}, headers=headers)
    assert r.status_code == 201, r.text
    assert balances(budget_id, category_id) == (Decimal("15000"), Decimal("3000"))

    assert client.post(f"/api/payments/{pid}/restore", headers=headers).status_code == 204
    assert balances(budget_id, category_id) == (Decimal("5000"), Decimal("3000"))


def test_deposit_into_an_expense_budget_is_refused(client):
    headers, _, _ = savings_setup(client)
    expense_budget = make_budget(client, headers, budget_type="expense")
    pid = capture(client, headers, DEPOSIT)["payment"]["id"]
    r = client.post(f"/api/payments/{pid}/savings", json={"budget_id": expense_budget}, headers=headers)
    assert r.status_code == 400
    assert balances(expense_budget) == Decimal("5000")


def test_undo_of_a_deposit_already_spent_is_refused(client):
    headers, budget_id, category_id = savings_setup(client, budget_amount=0, allocated=0)
    pid = capture(client, headers, DEPOSIT)["payment"]["id"]
    assert client.post(f"/api/payments/{pid}/savings", json={"budget_id": budget_id}, headers=headers).status_code == 201
    db = TestingSessionLocal()
    try:
        db.query(Budget).filter(Budget.id == budget_id).one().amount = Decimal("4000")
        db.commit()
    finally:
        db.close()
    r = client.post(f"/api/payments/{pid}/restore", headers=headers)
    assert r.status_code == 409
    assert balances(budget_id) == Decimal("4000")


def test_bank_messages_cannot_be_approved_as_expenses(client):
    headers, _, _ = savings_setup(client)
    expense = client.post("/api/categories/", json={"name": "Transport"}, headers=headers).json()
    pid = capture(client, headers, CARD)["payment"]["id"]
    assert client.post(f"/api/payments/{pid}/approve", json={"category_id": expense["id"]},
                       headers=headers).status_code == 400
    assert client.post(f"/api/payments/{pid}/recurring", json={"new": {"name": "Car", "category_id": expense["id"]}},
                       headers=headers).status_code == 400


def test_remembered_card_is_suggested_for_the_next_purchase(client):
    headers, budget_id, category_id = savings_setup(client)
    pid = capture(client, headers, CARD)["payment"]["id"]
    r = client.post(f"/api/payments/{pid}/savings", json={"category_id": category_id, "remember": True}, headers=headers)
    assert r.status_code == 201, r.text
    capture(client, headers, CARD.replace("Demo Motors Limited", "Demo Fuel Station").replace("1500.00", "800.00"))
    inbox = client.get(f"/api/payments/?budget_id={budget_id}", headers=headers).json()
    [p] = inbox["payments"]
    assert p["payee"] == "Demo Fuel Station" and p["suggested_category_id"] == category_id
    assert [c["id"] for c in inbox["savings_categories"]] == [category_id]
    assert [b["id"] for b in inbox["savings_budgets"]] == [budget_id]


def test_only_savings_budget_is_suggested_for_a_deposit(client):
    headers, budget_id, _ = savings_setup(client)
    capture(client, headers, DEPOSIT)
    [p] = client.get(f"/api/payments/?budget_id={budget_id}", headers=headers).json()["payments"]
    assert p["suggested_budget_id"] == budget_id


def test_same_card_purchase_twice_is_flagged_not_refused(client):
    headers, _, _ = savings_setup(client)
    capture(client, headers, CARD)
    assert capture(client, headers, CARD)["payment"]["possible_duplicate"] is True


def test_other_user_gets_404_on_savings_filing(client):
    headers, budget_id, category_id = savings_setup(client)
    other, _ = make_user(client)
    pid = capture(client, headers, DEPOSIT)["payment"]["id"]
    assert client.post(f"/api/payments/{pid}/savings", json={"budget_id": budget_id}, headers=other).status_code == 404
    own = capture(client, other, DEPOSIT)["payment"]["id"]
    assert client.post(f"/api/payments/{own}/savings", json={"budget_id": budget_id}, headers=other).status_code == 404
    card = capture(client, other, CARD)["payment"]["id"]
    assert client.post(f"/api/payments/{card}/savings", json={"category_id": category_id},
                       headers=other).status_code == 404
    assert balances(budget_id, category_id) == (Decimal("5000"), Decimal("3000"))
