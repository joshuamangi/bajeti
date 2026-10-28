from datetime import date
from decimal import Decimal

from app.utils.home_view import category_view, chart_order, home_view, month_meter, page_data
from app.utils.templates import money_text


def stats(id, name, allocated, used=0, balance=None, transfers_in=0, transfers_out=0, expenses=None):
    balance = allocated + transfers_in - transfers_out - used if balance is None else balance
    return {"id": id, "name": name, "allocated_amount": allocated, "used": used, "balance": balance,
            "total_transfers_in": transfers_in, "total_transfers_out": transfers_out,
            "expenses": expenses or [], "transfers_in": [], "transfers_out": [], "target": None}


class TestCategoryView:
    def test_expense_category_counts_spending_and_transfers(self):
        c = category_view(stats(1, "Groceries", 12000, used=8450.5, transfers_in=500), savings=False)
        assert c["available"] == Decimal("12500")
        assert c["balance"] == Decimal("4049.5")
        assert round(c["percent"], 1) == 67.6
        assert c["status"] == "ok"

    def test_over_spent_is_exceeded(self):
        c = category_view(stats(1, "Eating out", 3000, used=3450), savings=False)
        assert c["status"] == "exceeded"
        assert c["balance"] == Decimal("-450")

    def test_fully_used_is_zero(self):
        assert category_view(stats(1, "Rent", 25000, used=25000), savings=False)["status"] == "zero"

    def test_nothing_allocated_and_nothing_spent(self):
        c = category_view(stats(1, "Gifts", 0), savings=False)
        assert c["status"] == "zero" and c["percent"] == 0.0

    def test_savings_adds_withdrawals_back(self):
        # The API has already taken the withdrawal out of the allocation (25,000 -> 20,000).
        withdrawal = {"id": 9, "amount": 5000, "type": "withdrawal"}
        c = category_view(stats(8, "Holiday Trip", 20000, used=0, balance=20000, expenses=[withdrawal]), savings=True)
        assert c["used"] == Decimal("5000")
        assert c["available"] == Decimal("25000")
        assert c["percent"] == 20.0
        assert c["status"] == "ok" and c["savings"] is True


def test_chart_order_puts_exceeded_first_then_most_used():
    cats = [category_view(s, savings=False) for s in (
        stats(1, "Rent", 25000, used=25000),
        stats(2, "Groceries", 12000, used=6000),
        stats(3, "Eating out", 3000, used=3450),
        stats(4, "Health", 6000),
        stats(5, "Airtime", 1000, used=1000),
    )]
    assert [c["name"] for c in chart_order(cats)] == ["Eating out", "Airtime", "Rent", "Groceries", "Health"]


class TestMonthMeter:
    def test_on_track(self):
        m = month_meter(Decimal("100"), Decimal("50"), False, date(2026, 10, 27))
        assert (m["day"], m["days"], m["pace"]) == (27, 31, "ok")

    def test_ahead_of_the_month(self):
        assert month_meter(Decimal("100"), Decimal("60"), False, date(2026, 10, 10))["pace"] == "warn"

    def test_over_budget(self):
        assert month_meter(Decimal("100"), Decimal("101"), False, date(2026, 10, 30))["pace"] == "bad"

    def test_savings_has_no_pace(self):
        assert month_meter(Decimal("100"), Decimal("10"), True, date(2026, 10, 30))["pace"] is None


def test_home_view_totals_and_recent():
    expenses = [{"id": i, "amount": 100, "type": "spend", "description": f"e{i}", "created_at": f"2026-10-{i:02d}T10:00:00"}
                for i in range(1, 8)]
    budget = {"id": 1, "name": "Monthly", "type": "expense", "amount": 70000}
    v = home_view(budget, [stats(1, "Groceries", 12000, used=700, expenses=expenses), stats(2, "Rent", 25000)],
                  date(2026, 10, 27))
    assert v["allocated"] == Decimal("37000")
    assert v["unallocated"] == Decimal("33000")
    assert v["used"] == Decimal("700")
    assert [e["id"] for e in v["recent"]] == [7, 6, 5, 4, 3]
    assert v["recent"][0]["category_name"] == "Groceries"


def test_page_data_money_is_two_decimal_strings():
    budget = {"id": 1, "name": "Monthly", "type": "expense", "amount": 70000}
    v = home_view(budget, [stats(1, "Groceries", 12000, used=850.5)], date(2026, 10, 27))
    data = page_data(budget, [budget], v, "2026-10")
    c = data["categories"][0]
    assert (c["allocated"], c["used"], c["balance"]) == ("12000.00", "850.50", "11149.50")
    assert data["budget"]["amount"] == "70000.00" and data["unallocated"] == "58000.00"


class TestMoneyText:
    def test_whole_amounts_have_no_decimals(self):
        assert money_text(70000) == "70,000"

    def test_cents_show_two_decimals(self):
        assert money_text(1234.5) == "1,234.50"

    def test_negative_uses_a_minus_sign(self):
        assert money_text(-450) == "−450"

    def test_fixed_decimals_and_sign(self):
        assert money_text(4049.5, 0) == "4,050"
        assert money_text(500, sign=True) == "+500"

    def test_not_a_number_is_returned_as_is(self):
        assert money_text("abc") == "abc"

    def test_short_chart_labels(self):
        assert money_text(3360, short=True) == "3.4k"
        assert money_text(4000, short=True) == "4k"
        assert money_text(125000, short=True) == "125k"
        assert money_text(950, short=True) == "950"
