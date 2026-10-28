import re
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from data.db.models.models import Allocation, AllocationSnapshot, Category, Expense, Transfer
from services.analytics_rules import ZERO, category_summary, month_cell, percent, rankings
from services.budget_service import BudgetService
from services.category_service import CategoryService
from services.snapshot_service import SnapshotService

MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def shift_month(month: str, n: int) -> str:
    y, m = int(month[:4]), int(month[5:7]) + n
    while m < 1:
        m += 12
        y -= 1
    while m > 12:
        m -= 12
        y += 1
    return f"{y}-{m:02d}"


def last_months(end: str, n: int) -> list:
    return [shift_month(end, i - n + 1) for i in range(n)]


class AnalyticsService:
    """Spending per category and month for one budget. Expense budgets count spending,
    savings budgets count withdrawals. Every query is scoped by user_id."""

    @staticmethod
    def check_month(month: Optional[str]) -> str:
        if month is None:
            return SnapshotService.current_month()
        if not MONTH.match(month):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="Month must be YYYY-MM")
        return month

    @staticmethod
    def _budget(db: Session, user_id: int, budget_id: int):
        budget = BudgetService.get_budget_by_id(db=db, budget_id=budget_id, user_id=user_id)
        if not budget:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not Found")
        SnapshotService.record_current_month(db, budget.id)
        return budget

    @staticmethod
    def _categories(db: Session, user_id: int, budget) -> list:
        """(category, today's allocation) for the budget, by name."""
        rows = (db.query(Category, Allocation)
                .join(Allocation, Allocation.category_id == Category.id)
                .filter(Allocation.budget_id == budget.id, Category.user_id == user_id)
                .order_by(Category.name).all())
        return [(c, _money(a.allocated_amount)) for c, a in rows]

    @staticmethod
    def _grid(db: Session, user_id: int, budget, category_ids: list, months: list) -> dict:
        """{category_id: [cell per month]} with a fixed number of grouped queries."""
        if not category_ids or not months:
            return {cid: [] for cid in category_ids}
        expense_type = "withdrawal" if budget.type == "savings" else "spend"
        spent = {(cid, m): (_money(total), n) for cid, m, total, n in db.query(
            Expense.category_id, Expense.month, func.sum(Expense.amount), func.count(Expense.id))
            .filter(Expense.user_id == user_id, Expense.type == expense_type,
                    Expense.category_id.in_(category_ids), Expense.month.in_(months))
            .group_by(Expense.category_id, Expense.month).all()}

        def transfers(column):
            return {(cid, m): (n, _money(total)) for cid, m, n, total in db.query(
                column, Transfer.month, func.count(Transfer.id), func.sum(Transfer.amount))
                .filter(Transfer.user_id == user_id, column.in_(category_ids), Transfer.month.in_(months))
                .group_by(column, Transfer.month).all()}
        t_in, t_out = transfers(Transfer.to_category_id), transfers(Transfer.from_category_id)
        snapshots = {(s.category_id, s.month): _money(s.amount) for s in db.query(AllocationSnapshot).filter(
            AllocationSnapshot.budget_id == budget.id, AllocationSnapshot.month.in_(months)).all()}

        grid = {}
        for cid in category_ids:
            cells = []
            for m in months:
                amount, count = spent.get((cid, m), (ZERO, 0))
                tin, tout = t_in.get((cid, m), (0, ZERO)), t_out.get((cid, m), (0, ZERO))
                cells.append(month_cell(m, amount, snapshots.get((cid, m)), tin, tout,
                                        active=bool(count or tin[0] or tout[0])))
            grid[cid] = cells
        return grid

    @staticmethod
    def _has_spending_before(db: Session, user_id: int, budget, category_ids: list, month: str) -> bool:
        if not category_ids:
            return False
        expense_type = "withdrawal" if budget.type == "savings" else "spend"
        return db.query(Expense.id).filter(
            Expense.user_id == user_id, Expense.type == expense_type,
            Expense.category_id.in_(category_ids), Expense.month < month).first() is not None

    @staticmethod
    def _month_total(cells_by_cat: dict, index: int, key: str):
        values = [cells[index][key] for cells in cells_by_cat.values()]
        if key == "allocated" and all(v is None for v in values):
            return None
        return sum((v for v in values if v is not None), ZERO)

    @staticmethod
    def _budget_out(budget) -> dict:
        return {"id": budget.id, "name": budget.name, "type": budget.type}

    @staticmethod
    def month(db: Session, user_id: int, budget_id: int, month: Optional[str] = None) -> dict:
        month = AnalyticsService.check_month(month)
        budget = AnalyticsService._budget(db, user_id, budget_id)
        cats = AnalyticsService._categories(db, user_id, budget)
        ids = [c.id for c, _ in cats]
        months = last_months(month, 6)
        grid = AnalyticsService._grid(db, user_id, budget, ids, months)
        here, prev = 5, 4
        spent = AnalyticsService._month_total(grid, here, "spent") if ids else ZERO
        budgeted = AnalyticsService._month_total(grid, here, "allocated") if ids else None
        previous = AnalyticsService._month_total(grid, prev, "spent") if ids else ZERO
        rows = []
        for c, _ in cats:
            cell, before = grid[c.id][here], grid[c.id][prev]
            rows.append({
                "id": c.id, "name": c.name, "spent": cell["spent"], "allocated": cell["allocated"],
                "share_percent": percent(cell["spent"], spent) if spent else 0.0,
                "allocation_percent": cell["percent"], "over": cell["over"],
                "previous": before["spent"], "delta": cell["spent"] - before["spent"],
            })
        rows.sort(key=lambda r: (-r["spent"], r["name"].lower()))
        changes = sorted([r for r in rows if r["delta"]], key=lambda r: -abs(r["delta"]))[:3]
        return {
            "budget": AnalyticsService._budget_out(budget),
            "month": month,
            "current_month": SnapshotService.current_month(),
            "has_previous": AnalyticsService._has_spending_before(db, user_id, budget, ids, month),
            "spent": spent,
            "budgeted": budgeted,
            "used_percent": percent(spent, budgeted) if budgeted else None,
            "previous": {"month": months[prev], "spent": previous} if previous else None,
            "last6": [{"month": m, "spent": AnalyticsService._month_total(grid, i, "spent") if ids else ZERO,
                       "budgeted": AnalyticsService._month_total(grid, i, "allocated") if ids else None}
                      for i, m in enumerate(months)],
            "categories": rows,
            "changes": changes,
        }

    @staticmethod
    def trends(db: Session, user_id: int, budget_id: int, end: Optional[str] = None, months: int = 6) -> dict:
        end = AnalyticsService.check_month(end)
        if not 2 <= months <= 24:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="months must be between 2 and 24")
        budget = AnalyticsService._budget(db, user_id, budget_id)
        cats = AnalyticsService._categories(db, user_id, budget)
        span = last_months(end, months)
        grid = AnalyticsService._grid(db, user_id, budget, [c.id for c, _ in cats], span)
        summaries = [category_summary(c.id, c.name, allocated, grid[c.id]) for c, allocated in cats]
        return {"budget": AnalyticsService._budget_out(budget), "months": span,
                "categories": summaries, **rankings(summaries)}

    @staticmethod
    def year(db: Session, user_id: int, budget_id: int, year: Optional[int] = None) -> dict:
        this_year = int(SnapshotService.current_month()[:4])
        year = year or this_year
        if not 2000 <= year <= this_year:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Year out of range")
        budget = AnalyticsService._budget(db, user_id, budget_id)
        cats = AnalyticsService._categories(db, user_id, budget)
        ids = [c.id for c, _ in cats]
        last = SnapshotService.current_month() if year == this_year else f"{year}-12"
        months = [f"{year}-{m:02d}" for m in range(1, int(last[5:7]) + 1)]
        grid = AnalyticsService._grid(db, user_id, budget, ids, months)
        totals = [AnalyticsService._month_total(grid, i, "spent") if ids else ZERO for i in range(len(months))]
        total = sum(totals, ZERO)
        rows = []
        for c, allocated in cats:
            cells = grid[c.id]
            cat_total = sum((x["spent"] for x in cells), ZERO)
            if not cat_total:
                continue
            active = sum(1 for x in cells if x["spent"])
            rows.append({"id": c.id, "name": c.name, "total": cat_total,
                         "share_percent": percent(cat_total, total), "monthly_average": cat_total / active,
                         "allocated": allocated})
        rows.sort(key=lambda r: (-r["total"], r["name"].lower()))
        busiest = max(range(len(months)), key=lambda i: totals[i]) if total else None
        return {
            "budget": AnalyticsService._budget_out(budget),
            "year": year,
            "current_year": this_year,
            "has_previous": AnalyticsService._has_spending_before(db, user_id, budget, ids, f"{year}-01"),
            "total": total,
            "monthly_average": total / len(months),
            "budgeted": sum((a for _, a in cats), ZERO),
            "busiest": {"month": months[busiest], "spent": totals[busiest]} if busiest is not None else None,
            "months": [{"month": m, "spent": totals[i]} for i, m in enumerate(months)],
            "categories": rows,
        }

    @staticmethod
    def category(db: Session, user_id: int, category_id: int, month: Optional[str] = None) -> dict:
        month = AnalyticsService.check_month(month)
        category = CategoryService.get_category_by_id(db=db, category_id=category_id, user_id=user_id)
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not Found")
        allocation = db.query(Allocation).filter(Allocation.category_id == category.id).first()
        if not allocation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category has no budget")
        budget = AnalyticsService._budget(db, user_id, allocation.budget_id)
        current = SnapshotService.current_month()
        year_months = [f"{current[:4]}-{m:02d}" for m in range(1, int(current[5:7]) + 1)]
        six = last_months(current, 6)
        wanted = sorted(set(year_months) | set(six) | {month, shift_month(month, -1)})
        cells = dict(zip(wanted, AnalyticsService._grid(db, user_id, budget, [category.id], wanted)[category.id]))
        cell, before = cells[month], cells[shift_month(month, -1)]
        in_year = [cells[m] for m in year_months]
        year_total = sum((x["spent"] for x in in_year), ZERO)
        active = sum(1 for x in in_year if x["spent"])
        last6 = [cells[m] for m in six]
        expense_type = "withdrawal" if budget.type == "savings" else "spend"
        expenses = db.query(Expense).filter(
            Expense.user_id == user_id, Expense.category_id == category.id,
            Expense.month == month, Expense.type == expense_type).order_by(Expense.created_at.desc()).all()
        return {
            "budget": AnalyticsService._budget_out(budget),
            "category": {"id": category.id, "name": category.name, "allocated": _money(allocation.allocated_amount)},
            "month": month,
            "spent": cell["spent"],
            "allocated": cell["allocated"],
            "allocation_percent": cell["percent"],
            "previous_spent": before["spent"],
            "year": int(current[:4]),
            "year_total": year_total,
            "year_average": year_total / active if active else ZERO,
            "last6": {"over": sum(1 for x in last6 if x["over"]), "months": sum(1 for x in last6 if x["active"]),
                      "top_ups": sum(x["transfers_in"]["count"] for x in last6),
                      "topped_up": sum((x["transfers_in"]["total"] for x in last6), ZERO)},
            "year_months": [{"month": m, "spent": cells[m]["spent"], "allocated": cells[m]["allocated"]}
                            for m in year_months],
            "expenses": [{"id": e.id, "amount": _money(e.amount), "description": e.description,
                          "created_at": e.created_at} for e in expenses],
        }
