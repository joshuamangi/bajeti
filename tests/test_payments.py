"""Payment capture API. All messages are made up (fake names, numbers and codes)."""
import logging

from tests.helpers import first_budget_id, make_user

PAID = "QAB12CD3EF Confirmed. Ksh450.00 paid to Demo Grocer on 26/10/26 at 12:38 PM. New M-PESA balance is Ksh9,050.00. Transaction cost, Ksh0.00."
SENT = "QAB12CD3EH Confirmed. Ksh300.00 sent to DEMO PERSON 0700000000 on 27/10/26 at 9:02 AM. Transaction cost, Ksh7.00."
RECEIVED = "QAB12CD3EQ Confirmed.You have received Ksh5,000.00 from DEMO PERSON 0744444444 on 27/10/26 at 1:00 PM."


def category(client, headers, name, amount=5000.0):
    budget_id = first_budget_id(client, headers)
    c = client.post("/api/categories/", json={"name": name}, headers=headers).json()
    client.post(f"/api/budgets/{budget_id}/allocations/", json={"category_id": c["id"], "allocated_amount": amount},
                headers=headers)
    return budget_id, c["id"]


def capture(client, headers, raw):
    return client.post("/api/payments/capture", json={"raw": raw}, headers=headers)


def expenses(client, headers, category_id):
    r = client.get(f"/api/expenses/category/{category_id}", headers=headers)
    return [] if r.status_code == 404 else r.json()


def test_capture_adds_to_the_inbox_with_a_suggestion(client):
    headers, _ = make_user(client)
    budget_id, groceries = category(client, headers, "Groceries")
    r = capture(client, headers, PAID)
    assert r.status_code == 201 and r.json()["payment"]["payee"] == "Demo Grocer"
    inbox = client.get(f"/api/payments/?budget_id={budget_id}", headers=headers).json()
    [p] = inbox["payments"]
    assert (p["amount"], p["reference"], p["suggested_category_id"]) == ("450.00", "QAB12CD3EF", groceries)
    assert client.get("/api/payments/count", headers=headers).json() == {"pending": 1}


def test_same_reference_twice_is_refused(client):
    headers, _ = make_user(client)
    capture(client, headers, PAID)
    r = capture(client, headers, PAID)
    assert r.status_code == 409 and "Already captured: QAB12CD3EF" in r.json()["detail"]


def test_money_received_is_not_added(client):
    headers, _ = make_user(client)
    r = capture(client, headers, RECEIVED)
    assert r.status_code == 200 and r.json()["added"] is False and "received" in r.json()["reason"]
    assert client.get("/api/payments/count", headers=headers).json() == {"pending": 0}


def test_unreadable_text_stays_in_the_inbox(client):
    headers, _ = make_user(client)
    r = capture(client, headers, "Malipo ya Ksh 200.00 yamefanikiwa kwa Duka la Demo")
    assert r.status_code == 201
    [p] = client.get("/api/payments/", headers=headers).json()["payments"]
    assert p["kind"] == "unknown" and p["raw_text"]


def test_approve_records_the_month_splits_the_fee_and_forgets_the_text(client):
    headers, _ = make_user(client)
    _, household = category(client, headers, "Household")
    pid = capture(client, headers, SENT).json()["payment"]["id"]
    r = client.post(f"/api/payments/{pid}/approve", json={"category_id": household}, headers=headers)
    assert r.status_code == 201
    assert (r.json()["amount"], r.json()["fee"], r.json()["month"]) == ("300.00", "7.00", "2026-10")
    # The fee is its own expense in "M-Pesa fees" (tests/test_fees_recurring.py).
    [e] = expenses(client, headers, household)
    assert (float(e["amount"]), e["description"], e["month"]) == (300.0, "DEMO PERSON", "2026-10")
    assert client.get("/api/payments/", headers=headers).json()["payments"] == []
    # Approving again is refused.
    assert client.post(f"/api/payments/{pid}/approve", json={"category_id": household}, headers=headers).status_code == 409


def test_restore_after_approve_removes_the_expense(client):
    headers, _ = make_user(client)
    _, household = category(client, headers, "Household")
    pid = capture(client, headers, SENT).json()["payment"]["id"]
    client.post(f"/api/payments/{pid}/approve", json={"category_id": household}, headers=headers)
    assert client.post(f"/api/payments/{pid}/restore", headers=headers).status_code == 204
    assert expenses(client, headers, household) == []
    [p] = client.get("/api/payments/", headers=headers).json()["payments"]
    assert p["raw_text"] is None  # the original text is not brought back


def test_remember_payee_suggests_next_time(client):
    headers, _ = make_user(client)
    budget_id, household = category(client, headers, "Household")
    pid = capture(client, headers, SENT).json()["payment"]["id"]
    client.post(f"/api/payments/{pid}/approve", json={"category_id": household, "remember": True}, headers=headers)
    capture(client, headers, SENT.replace("QAB12CD3EH", "QAB12CD3ZZ"))
    [p] = client.get(f"/api/payments/?budget_id={budget_id}", headers=headers).json()["payments"]
    assert p["suggested_category_id"] == household


def test_dismiss_forgets_the_text(client):
    headers, _ = make_user(client)
    pid = capture(client, headers, PAID).json()["payment"]["id"]
    assert client.post(f"/api/payments/{pid}/dismiss", headers=headers).status_code == 204
    assert client.get("/api/payments/count", headers=headers).json() == {"pending": 0}


def test_savings_categories_are_refused(client):
    headers, _ = make_user(client)
    c = client.post("/api/categories/", json={"name": "Holiday", "type": "savings"}, headers=headers).json()
    pid = capture(client, headers, PAID).json()["payment"]["id"]
    assert client.post(f"/api/payments/{pid}/approve", json={"category_id": c["id"]}, headers=headers).status_code == 400


def test_messages_are_not_logged(client, caplog):
    headers, _ = make_user(client)
    with caplog.at_level(logging.DEBUG):
        capture(client, headers, PAID.replace("QAB12CD3EF", "QAB12LOG99"))
    assert "Demo Grocer" not in caplog.text and "QAB12LOG99" not in caplog.text


def test_other_user_gets_404_everywhere(client):
    headers, _ = make_user(client)
    budget_id, groceries = category(client, headers, "Groceries")
    pid = capture(client, headers, PAID).json()["payment"]["id"]
    other, _ = make_user(client)
    _, mine = category(client, other, "Mine")
    assert client.get(f"/api/payments/?budget_id={budget_id}", headers=other).status_code == 404
    assert client.post(f"/api/payments/{pid}/approve", json={"category_id": mine}, headers=other).status_code == 404
    assert client.post(f"/api/payments/{pid}/dismiss", headers=other).status_code == 404
    assert client.post(f"/api/payments/{pid}/restore", headers=other).status_code == 404
    # B cannot file their own payment into A's category either.
    theirs = capture(client, other, SENT).json()["payment"]["id"]
    assert client.post(f"/api/payments/{theirs}/approve", json={"category_id": groceries}, headers=other).status_code == 404
    # B's inbox does not show A's payment, and A's payment is untouched.
    assert [p["id"] for p in client.get("/api/payments/", headers=other).json()["payments"]] == [theirs]
    assert client.get("/api/payments/count", headers=headers).json() == {"pending": 1}
    # The same reference is fine for a different user.
    assert capture(client, other, PAID).status_code == 201


FIBRE = "Your payment of KES 3,500.00 to Demo Fibre Internet was successful."


def test_same_details_without_a_reference_is_flagged_not_refused(client):
    headers, _ = make_user(client)
    first = capture(client, headers, FIBRE)
    second = capture(client, headers, FIBRE)
    assert first.status_code == second.status_code == 201
    assert first.json()["payment"]["possible_duplicate"] is False
    assert second.json()["payment"]["possible_duplicate"] is True
    assert "looks like one already in Bajeti" in second.json()["message"]
    flags = {p["id"]: p["possible_duplicate"] for p in client.get("/api/payments/", headers=headers).json()["payments"]}
    assert flags == {first.json()["payment"]["id"]: False, second.json()["payment"]["id"]: True}


def test_a_different_amount_or_a_dismissed_earlier_one_is_not_a_duplicate(client):
    headers, _ = make_user(client)
    first = capture(client, headers, FIBRE).json()["payment"]["id"]
    other = capture(client, headers, FIBRE.replace("3,500.00", "1,200.00")).json()["payment"]
    assert other["possible_duplicate"] is False
    client.post(f"/api/payments/{first}/dismiss", headers=headers)
    assert capture(client, headers, FIBRE).json()["payment"]["possible_duplicate"] is False


def test_messages_with_a_reference_are_never_flagged(client):
    headers, _ = make_user(client)
    assert capture(client, headers, PAID).json()["payment"]["possible_duplicate"] is False
