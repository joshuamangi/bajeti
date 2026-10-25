from decimal import Decimal

TERMS = ("short_term", "mid_term", "long_term")


def target_totals(categories_with_stats: list) -> dict:
    """Sum the short, mid and long term targets of the categories on the dashboard.

    Categories without a target, and terms without an amount, count as 0.
    """
    totals = {term: Decimal("0") for term in TERMS}
    for category in categories_with_stats:
        target = category.get("target") or {}
        for term in TERMS:
            progress = target.get(term)
            if progress:
                totals[term] += Decimal(str(progress["amount"]))
    return totals
