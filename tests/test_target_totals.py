from decimal import Decimal

from app.utils.target_totals import target_totals


def _term(amount):
    return {"amount": amount, "percent": 0.0, "remaining": amount}


def test_no_categories_gives_zero_totals():
    assert target_totals([]) == {
        "short_term": Decimal("0"), "mid_term": Decimal("0"), "long_term": Decimal("0")}


def test_sums_each_horizon_and_treats_empty_as_zero():
    categories = [
        {"target": {"id": 1, "short_term": _term("200.00"), "mid_term": _term("400.50"), "long_term": None}},
        {"target": {"id": 2, "short_term": _term("100.25"), "mid_term": None, "long_term": None}},
        {"target": {"id": 3, "short_term": None, "mid_term": None, "long_term": None}},
        {"target": None},
        {},
    ]

    assert target_totals(categories) == {
        "short_term": Decimal("300.25"), "mid_term": Decimal("400.50"), "long_term": Decimal("0")}
