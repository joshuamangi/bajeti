# app/utils/home_view.py
"""Numbers for the Home page (Prototype A, PORT-GUIDE §5.2), built from the
categories-with-stats API response. Pure functions so they can be tested alone."""
import calendar
from datetime import date
from decimal import Decimal


def _d(value) -> Decimal:
    return Decimal(str(value or 0))


def category_view(category: dict, savings: bool) -> dict:
    """Available, used, balance, percent and status for one category this month.

    Expense budgets count spending. Savings budgets count withdrawals, which the API has
    already taken out of the allocation, so they are added back to get what was available."""
    expenses = category.get("expenses") or []
    allocated = _d(category.get("allocated_amount"))
    net_transfers = _d(category.get("total_transfers_in")) - _d(category.get("total_transfers_out"))
    balance = _d(category.get("balance"))
    if savings:
        used = sum((_d(e["amount"]) for e in expenses if e.get("type") == "withdrawal"), Decimal("0"))
        available = allocated + used + net_transfers
    else:
        used = _d(category.get("used"))
        available = allocated + net_transfers
    if available > 0:
        percent = float(used / available * 100)
    else:
        percent = 100.0 if used > 0 else 0.0
    if balance < 0:
        status = "exceeded"
    elif available == 0 or (balance == 0 and available > 0):
        status = "zero"
    else:
        status = "ok"
    return {
        "id": category["id"],
        "name": category["name"],
        "allocated": allocated,
        "available": available,
        "used": used,
        "balance": balance,
        "percent": percent,
        "status": status,
        "savings": savings,
        "transfers_in": category.get("transfers_in") or [],
        "transfers_out": category.get("transfers_out") or [],
        "expenses": expenses,
        "target": category.get("target"),
    }


def chart_order(categories: list) -> list:
    """Most used first: exceeded categories first, then by percent used, then by name."""
    def rank(c):
        if c["available"]:
            score = c["percent"]
        else:
            score = 999 if c["used"] else -1
        return (1000 if c["status"] == "exceeded" else 0) + score
    return sorted(categories, key=lambda c: (-rank(c), c["name"].lower()))


def month_meter(allocated: Decimal, used: Decimal, savings: bool, today: date) -> dict:
    """The month bar: share of the allocation used, where today sits in the month, and the pace."""
    days = calendar.monthrange(today.year, today.month)[1]
    month_percent = today.day / days * 100
    percent = float(used / allocated * 100) if allocated else 0.0
    if savings:
        pace = None
    elif percent > 100:
        pace = "bad"
    elif percent > month_percent + 5:
        pace = "warn"
    else:
        pace = "ok"
    return {
        "percent": percent,
        "day": today.day,
        "days": days,
        "days_left": days - today.day,
        "month_percent": month_percent,
        "pace": pace,
    }


def _money(value) -> str:
    return format(_d(value).quantize(Decimal("0.01")), "f")


def page_data(budget: dict, budgets: list, view: dict, month: str) -> dict:
    """JSON for the sheets the browser draws (add expense, category, transfer). Money is a
    string with two decimals so nothing is rounded on the way through float."""
    def transfers(c):
        rows = [{"direction": "in", "other": t.get("from_category_name"), "amount": _money(t["amount"]),
                 "description": t.get("description")} for t in c["transfers_in"]]
        rows += [{"direction": "out", "other": t.get("to_category_name"), "amount": _money(t["amount"]),
                  "description": t.get("description")} for t in c["transfers_out"]]
        return rows

    return {
        "month": month,
        "budget": {"id": budget["id"], "name": budget["name"], "type": budget["type"],
                   "amount": _money(budget["amount"])},
        "budgets": [{"id": b["id"], "name": b["name"], "type": b["type"], "amount": _money(b["amount"])}
                    for b in budgets],
        "unallocated": _money(view["unallocated"]),
        "categories": [{
            "id": c["id"],
            "name": c["name"],
            "allocated": _money(c["allocated"]),
            "available": _money(c["available"]),
            "used": _money(c["used"]),
            "balance": _money(c["balance"]),
            "percent": round(c["percent"], 1),
            "status": c["status"],
            "savings": c["savings"],
            "target": c["target"],
            "transfers": transfers(c),
            "expenses": [{"id": e["id"], "amount": _money(e["amount"]), "description": e.get("description") or "",
                          "type": e.get("type"), "month": e.get("month"), "created_at": str(e.get("created_at") or "")}
                         for e in c["expenses"]],
        } for c in view["table"]],
    }


def home_view(budget: dict, categories_with_stats: list, today: date) -> dict:
    """Everything the Home page shows for the active budget."""
    savings = budget.get("type") == "savings"
    categories = [category_view(c, savings) for c in categories_with_stats]
    allocated = sum((c["allocated"] for c in categories), Decimal("0"))
    if savings:
        # Withdrawals are already out of the allocations; add them back for the month total.
        allocated += sum((c["used"] for c in categories), Decimal("0"))
    used = sum((c["used"] for c in categories), Decimal("0"))
    balance = sum((c["balance"] for c in categories), Decimal("0"))
    recent = sorted(
        ({**e, "category_name": c["name"]} for c in categories for e in c["expenses"]),
        key=lambda e: (str(e.get("created_at") or ""), e.get("id") or 0),
        reverse=True,
    )[:5]
    return {
        "savings": savings,
        "categories": categories,
        "chart": chart_order(categories),
        "table": sorted(categories, key=lambda c: c["name"].lower()),
        "allocated": allocated,
        "used": used,
        "balance": balance,
        "unallocated": _d(budget.get("amount")) - sum((c["allocated"] for c in categories), Decimal("0")),
        "meter": month_meter(allocated, used, savings, today),
        "recent": recent,
        "targets": [c for c in categories if c["target"]],
    }
