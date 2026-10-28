"""Analytics rules from Prototype A (catMonth, squeezeRows; PORT-GUIDE §5.7 and §9).

Pure functions on Decimals so they can be tested without a database. A month's allocation
is None when no snapshot exists for it; such months count as spending but are never
"over", "tight" or "squeezed".
"""
from decimal import Decimal, ROUND_CEILING
from typing import Optional

ZERO = Decimal("0")


def percent(part: Decimal, whole: Optional[Decimal]) -> Optional[float]:
    if whole is None:
        return None
    if whole > 0:
        return float(part / whole * 100)
    return 100.0 if part > 0 else 0.0


def month_cell(month: str, spent: Decimal, allocated: Optional[Decimal],
               transfers_in: tuple, transfers_out: tuple, active: bool) -> dict:
    """One category in one month. transfers_in/out are (count, total)."""
    tin_n, tin = transfers_in
    tout_n, tout = transfers_out
    known = allocated is not None
    return {
        "month": month,
        "spent": spent,
        "allocated": allocated,
        "transfers_in": {"count": tin_n, "total": tin},
        "transfers_out": {"count": tout_n, "total": tout},
        "active": active,
        "percent": percent(spent, allocated),
        # Spent more than allocated (top-ups do not change this: it measures the plan).
        "over": known and spent > allocated,
        # Still over after top-ups in and money moved out.
        "uncovered": known and spent > allocated + tin - tout,
        # 90 to 99 percent. Exactly 100 is neutral: fixed bills landing on plan.
        "tight": known and allocated > 0 and allocated * Decimal("0.9") <= spent < allocated,
    }


def round_up(amount: Decimal, step: int = 100) -> Decimal:
    return (amount / step).to_integral_value(rounding=ROUND_CEILING) * step


def category_summary(category_id: int, name: str, allocated: Decimal, cells: list) -> dict:
    """Totals over a run of months for one category. allocated is today's allocation."""
    active = [c for c in cells if c["active"]]
    total = sum((c["spent"] for c in cells), ZERO)
    average = total / len(active) if active else ZERO
    suggested = round_up(average)
    return {
        "id": category_id,
        "name": name,
        "allocated": allocated,
        "cells": cells,
        "months": len(active),
        "over": sum(1 for c in cells if c["over"]),
        "uncovered": sum(1 for c in cells if c["uncovered"]),
        "top_ups": sum(c["transfers_in"]["count"] for c in cells),
        "topped_up": sum((c["transfers_in"]["total"] for c in cells), ZERO),
        "gave_count": sum(c["transfers_out"]["count"] for c in cells),
        "gave": sum((c["transfers_out"]["total"] for c in cells), ZERO),
        "total": total,
        "average": average,
        "average_percent": percent(average, allocated) if allocated else 0.0,
        # Tip: allocate about the average rounded up to 100 if that is more than today.
        "suggested": suggested if suggested > allocated else None,
    }


def rankings(summaries: list) -> dict:
    """The 6-month insights: squeezed categories, room to spare, transfers both ways."""
    def pressure(s):
        return (-s["over"], -s["top_ups"], -(s["average_percent"] or 0))
    return {
        "squeezed": sorted([s for s in summaries if s["over"] >= 2], key=pressure),
        "room_to_spare": sorted(
            [s for s in summaries if s["months"] >= 4 and s["allocated"] > 0 and s["average_percent"] < 60],
            key=lambda s: s["average_percent"]),
        "order": sorted(summaries, key=lambda s: pressure(s) + (s["name"].lower(),)),
        "topped_up_most": sorted([s for s in summaries if s["top_ups"]],
                                 key=lambda s: (-s["top_ups"], -s["topped_up"])),
        "gave_most": sorted([s for s in summaries if s["gave_count"]],
                            key=lambda s: (-s["gave_count"], -s["gave"])),
    }
