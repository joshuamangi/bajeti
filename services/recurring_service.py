import calendar
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from data.db.models.models import Allocation, Category, Expense, RecurringExpense, RecurringRun
from schema.recurring import RecurringCreate
from services.budget_service import BudgetService
from services.category_service import CategoryService



def today() -> date:
    """Today in the household's time zone (Nairobi, UTC+3, no daylight saving)."""
    tz = timezone(timedelta(hours=settings.APP_TIMEZONE_OFFSET_HOURS))
    return datetime.now(tz).date()


def month_day(year: int, month: int, anchor_day: int) -> date:
    """The anchor day in that month, or the month's last day if it is shorter (31 -> 28 Feb)."""
    return date(year, month, min(anchor_day, calendar.monthrange(year, month)[1]))


def next_month(due: date, anchor_day: int) -> date:
    year, month = (due.year + 1, 1) if due.month == 12 else (due.year, due.month + 1)
    return month_day(year, month, anchor_day)


def due_dates(next_due: date, anchor_day: int, until: date) -> list:
    """Every due date from next_due up to and including `until`."""
    dates, d = [], next_due
    while d <= until:
        dates.append(d)
        d = next_month(d, anchor_day)
    return dates


class RecurringService:

    @staticmethod
    def _get(db: Session, user_id: int, recurring_id: int) -> RecurringExpense:
        item = db.query(RecurringExpense).filter(
            RecurringExpense.id == recurring_id, RecurringExpense.user_id == user_id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring expense not found")
        return item

    @staticmethod
    def _check_category(db: Session, user_id: int, category_id: int) -> Category:
        category = CategoryService.get_category_by_id(db=db, category_id=category_id, user_id=user_id)
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not Found")
        if category.type != "expense":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Recurring expenses use expense categories only")
        return category

    @staticmethod
    def out(item: RecurringExpense, category_name: str, **extra) -> dict:
        return {"id": item.id, "name": item.name, "amount": Decimal(str(item.amount)), "category_id": item.category_id,
                "category_name": category_name, "next_due": item.next_due, "anchor_day": item.anchor_day,
                "mode": item.mode, "paused": item.paused, **extra}

    @staticmethod
    def _names(db: Session, items: list) -> dict:
        ids = {i.category_id for i in items}
        return {c.id: c.name for c in db.query(Category).filter(Category.id.in_(ids)).all()} if ids else {}

    @staticmethod
    def create(db: Session, user_id: int, data: RecurringCreate) -> dict:
        category = RecurringService._check_category(db, user_id, data.category_id)
        item = RecurringExpense(user_id=user_id, category_id=category.id, name=data.name.strip(),
                                amount=data.amount, anchor_day=data.next_due.day, next_due=data.next_due,
                                mode=data.mode, paused=False)
        db.add(item)
        db.commit()
        db.refresh(item)
        return RecurringService.out(item, category.name)

    @staticmethod
    def update(db: Session, user_id: int, recurring_id: int, data: RecurringCreate) -> dict:
        item = RecurringService._get(db, user_id, recurring_id)
        category = RecurringService._check_category(db, user_id, data.category_id)
        # A new amount applies to future payments only; recorded expenses keep theirs.
        item.name, item.amount, item.category_id = data.name.strip(), data.amount, category.id
        item.next_due, item.anchor_day, item.mode = data.next_due, data.next_due.day, data.mode
        db.commit()
        return RecurringService.out(item, category.name)

    @staticmethod
    def delete(db: Session, user_id: int, recurring_id: int):
        item = RecurringService._get(db, user_id, recurring_id)
        db.query(RecurringRun).filter(RecurringRun.recurring_id == item.id).delete()
        db.delete(item)
        db.commit()

    @staticmethod
    def set_paused(db: Session, user_id: int, recurring_id: int, paused: bool) -> dict:
        item = RecurringService._get(db, user_id, recurring_id)
        item.paused = paused
        db.commit()
        return RecurringService.out(item, RecurringService._names(db, [item]).get(item.category_id, ""))

    @staticmethod
    def _in_budget(db: Session, user_id: int, budget_id: Optional[int]) -> list:
        query = db.query(RecurringExpense).filter(RecurringExpense.user_id == user_id)
        if budget_id is not None:
            budget = BudgetService.get_budget_by_id(db=db, budget_id=budget_id, user_id=user_id)
            if not budget:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not Found")
            category_ids = [a.category_id for a in db.query(Allocation).filter(Allocation.budget_id == budget.id)]
            query = query.filter(RecurringExpense.category_id.in_(category_ids))
        return query.all()

    @staticmethod
    def _skip_recorded(db: Session, item: RecurringExpense):
        """Move next_due past dates that already have a run (after an undo of an older one)."""
        done = {r.due_date for r in db.query(RecurringRun).filter(RecurringRun.recurring_id == item.id)}
        while item.next_due in done:
            item.next_due = next_month(item.next_due, item.anchor_day)

    @staticmethod
    def _record(db: Session, item: RecurringExpense, due_date: date, action: str):
        """Write the run (and the expense) for one due date in one transaction."""
        if due_date != item.next_due:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already recorded")
        expense = None
        amount = Decimal(str(item.amount))
        if action in ("approved", "auto"):
            now = datetime.utcnow()
            expense = Expense(user_id=item.user_id, category_id=item.category_id, amount=amount,
                              description=item.name, month=due_date.strftime("%Y-%m"), type="spend",
                              created_at=now, updated_at=now)
            db.add(expense)
            db.flush()
        db.add(RecurringRun(recurring_id=item.id, user_id=item.user_id, due_date=due_date, action=action,
                            expense_id=expense.id if expense else None,
                            amount=amount if expense else None))
        item.next_due = next_month(due_date, item.anchor_day)
        RecurringService._skip_recorded(db, item)
        try:
            db.commit()
        except IntegrityError:
            # Two tabs approving at once: the unique (recurring_id, due_date) row wins once.
            db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already recorded")

    @staticmethod
    def record_auto(db: Session, user_id: int, budget_id: Optional[int] = None):
        """Add auto items whose due date has come. Runs when a page loads (no background job)."""
        for item in RecurringService._in_budget(db, user_id, budget_id):
            if item.mode != "auto" or item.paused:
                continue
            for due in due_dates(item.next_due, item.anchor_day, today()):
                RecurringService._record(db, item, due, "auto")

    @staticmethod
    def due(db: Session, user_id: int, budget_id: Optional[int]) -> list:
        RecurringService.record_auto(db, user_id, budget_id)
        items = [i for i in RecurringService._in_budget(db, user_id, budget_id)
                 if i.mode == "ask_first" and not i.paused
                 and i.next_due <= today()]  # on the due date, not before
        names = RecurringService._names(db, items)
        out = [RecurringService.out(i, names.get(i.category_id, ""), due_date=i.next_due,
                                    days=(i.next_due - today()).days,
                                    overdue=len(due_dates(i.next_due, i.anchor_day, today())))
               for i in items]
        return sorted(out, key=lambda x: (x["due_date"], x["name"].lower()))

    @staticmethod
    def list(db: Session, user_id: int, budget_id: Optional[int]) -> dict:
        RecurringService.record_auto(db, user_id, budget_id)
        items = RecurringService._in_budget(db, user_id, budget_id)
        names = RecurringService._names(db, items)
        ids = [i.id for i in items]
        runs = (db.query(RecurringRun, RecurringExpense.name).join(RecurringExpense)
                .filter(RecurringRun.user_id == user_id, RecurringRun.recurring_id.in_(ids))
                .order_by(RecurringRun.created_at.desc(), RecurringRun.id.desc()).limit(10).all()) if ids else []
        active = [i for i in items if not i.paused]
        return {
            "items": [RecurringService.out(i, names.get(i.category_id, ""))
                      for i in sorted(items, key=lambda i: (i.paused, i.next_due, i.name.lower()))],
            "monthly_total": sum((Decimal(str(i.amount)) for i in active), Decimal("0")),
            "active_count": len(active),
            "recent": [{"recurring_id": r.recurring_id, "name": name, "due_date": r.due_date, "action": r.action,
                        "amount": None if r.amount is None else Decimal(str(r.amount))} for r, name in runs],
        }

    @staticmethod
    def approve(db: Session, user_id: int, recurring_id: int, due_date: date, action: str = "approved"):
        item = RecurringService._get(db, user_id, recurring_id)
        if item.paused:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This recurring expense is paused")
        RecurringService._record(db, item, due_date, action)

    @staticmethod
    def approve_all(db: Session, user_id: int, recurring_id: int) -> int:
        """Record every due date up to today, each in its own month."""
        item = RecurringService._get(db, user_id, recurring_id)
        dates = due_dates(item.next_due, item.anchor_day, today())
        for due in dates:
            RecurringService._record(db, item, due, "approved")
        return len(dates)

    @staticmethod
    def undo(db: Session, user_id: int, recurring_id: int, due_date: date):
        """Undo an approval or a skip: remove the expense and the run, and make the date due again."""
        item = RecurringService._get(db, user_id, recurring_id)
        run = db.query(RecurringRun).filter(RecurringRun.recurring_id == item.id,
                                            RecurringRun.due_date == due_date).first()
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nothing recorded for that date")
        if run.expense_id:
            expense = db.query(Expense).filter(Expense.id == run.expense_id, Expense.user_id == user_id).first()
            if expense:
                db.delete(expense)
        db.delete(run)
        if due_date < item.next_due:
            item.next_due = due_date
        db.commit()

    @staticmethod
    def count_for_category(db: Session, user_id: int, category_id: int) -> int:
        return db.query(RecurringExpense).filter(RecurringExpense.user_id == user_id,
                                                 RecurringExpense.category_id == category_id).count()
