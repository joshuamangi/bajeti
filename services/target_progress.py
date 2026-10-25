from decimal import Decimal
from typing import Optional

TERMS = ("short_term", "mid_term", "long_term")


def term_progress(target_amount: Optional[Decimal], current: Decimal) -> Optional[dict]:
    """Progress of `current` toward one target amount, or None when the term has no target.

    percent is not capped (110.0 means the target is exceeded); remaining never goes below zero."""
    if target_amount is None or target_amount <= 0:
        return None
    current = max(Decimal(current), Decimal("0"))
    amount = Decimal(target_amount)
    percent = (current / amount * 100).quantize(Decimal("0.1"))
    return {
        "amount": amount,
        "percent": float(percent),
        "remaining": max(amount - current, Decimal("0")),
    }


def target_progress(target, current: Decimal) -> dict:
    """The shape returned as `target` in the category stats."""
    return {
        "id": target.id,
        **{term: term_progress(getattr(target, f"{term}_amount"), current) for term in TERMS},
    }
