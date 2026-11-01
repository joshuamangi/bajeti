import calendar
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from data.db.models.models import (Allocation, Budget, Category, Expense, PayeeRule, PendingPayment,
                                   RecurringExpense, RecurringRun)
from schema.payment import ApproveIn, CaptureIn, RecurringIn, SavingsIn
from services.budget_service import BudgetService
from services.category_service import CategoryService
from services.payment_parser import parse
from services.fee_service import FEE_CATEGORY, FeeService
from services.recurring_service import RecurringService, month_day, today

# Payee words -> category name, matched in the active budget (from the prototype).
KEYWORDS = [
    (re.compile(r"grocer|supermarket|mart|market|duka", re.I), "Groceries"),
    (re.compile(r"pharm|clinic|hospital|chemist", re.I), "Health"),
    (re.compile(r"fuel|petrol|shell|rubis|matatu|taxi", re.I), "Transport"),
    (re.compile(r"power|water|internet|fibre|wifi", re.I), "Utilities"),
    (re.compile(r"cinema|movie|stream", re.I), "Entertainment"),
]

# Bank messages (kind -> what they do to savings): money from a bank to M-Pesa and card purchases
# are withdrawals from a savings category, a deposit adds to a savings budget's amount.
SAVINGS = {"received": "withdrawal", "card": "withdrawal", "deposit": "deposit"}


def _money(value) -> Optional[Decimal]:
    return None if value is None else Decimal(str(value)).quantize(Decimal("0.01"))


def _payee_key(payee: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (payee or "").strip().lower())


def _month_label(d: date) -> str:
    return f"{calendar.month_name[d.month]} {d.year}"


def _ksh(value) -> str:
    return f"Ksh {_money(value):,}"


def _capture_message(p: PendingPayment, duplicate: bool) -> str:
    """One line the iPhone Shortcut shows after sending a message."""
    if p.amount is None:
        return "Couldn't read this message. It is in Payments for you to fill in."
    fee = _money(p.fee)
    if SAVINGS.get(p.kind) == "deposit":
        text = f"Added deposit to {p.account or 'savings'}: Ksh {_money(p.amount):,}"
    elif p.kind in SAVINGS:
        text = f"Added savings withdrawal {p.payee or p.account or ''}: Ksh {_money(p.amount):,}".replace("  ", " ")
    else:
        text = f"Added {p.payee or 'payment'}: Ksh {_money(p.amount):,}"
    if fee:
        text += f" + {fee:,} fee"
    if duplicate:
        return text + ". It looks like one already in Bajeti, so check before you approve."
    return text + ". Approve it in Bajeti."


class PaymentService:

    @staticmethod
    def _get(db: Session, user_id: int, payment_id: int) -> PendingPayment:
        payment = db.query(PendingPayment).filter(
            PendingPayment.id == payment_id, PendingPayment.user_id == user_id).first()
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        return payment

    @staticmethod
    def possible_duplicate(db: Session, p: PendingPayment) -> bool:
        """A message with no reference cannot be deduplicated, so flag (not refuse) an earlier
        payment with the same amount, payee and date. Two equal purchases in a day can be real."""
        if p.reference or p.amount is None:
            return False
        query = db.query(PendingPayment.id).filter(
            PendingPayment.user_id == p.user_id, PendingPayment.id < p.id,
            PendingPayment.status != "dismissed", PendingPayment.amount == p.amount)
        query = query.filter(PendingPayment.payee == p.payee if p.payee else PendingPayment.payee.is_(None))
        query = query.filter(PendingPayment.paid_on == p.paid_on if p.paid_on else PendingPayment.paid_on.is_(None))
        query = query.filter(PendingPayment.account == p.account if p.account else PendingPayment.account.is_(None))
        return query.first() is not None

    @staticmethod
    def out(p: PendingPayment, suggested: Optional[int] = None, duplicate: bool = False,
            suggested_recurring: Optional[int] = None, suggested_budget: Optional[int] = None) -> dict:
        amount, fee = _money(p.amount), _money(p.fee)
        return {
            "id": p.id, "source": p.source, "kind": p.kind, "status": p.status,
            "amount": amount, "fee": fee,
            "total": (amount + (fee or Decimal("0"))) if amount is not None else None,
            "payee": p.payee, "account": p.account, "savings": SAVINGS.get(p.kind),
            "reference": p.reference, "paid_on": p.paid_on,
            "received_at": p.received_at, "raw_text": p.raw_text,
            "suggested_category_id": suggested,
            "suggested_recurring_id": suggested_recurring,
            "suggested_budget_id": suggested_budget,
            "possible_duplicate": duplicate,
        }

    @staticmethod
    def capture(db: Session, user_id: int, data: CaptureIn) -> tuple:
        """Returns (http status, body). 201 added, 200 ignored with a reason, 409 already captured.
        Every body has a one-line "message" for the iPhone Shortcut."""
        parsed = parse(data.raw)
        if parsed.get("ignored"):
            return status.HTTP_200_OK, {"added": False, "kind": parsed["kind"], "reason": parsed["ignored"],
                                        "message": parsed["ignored"]}
        if parsed["reference"]:
            existing = db.query(PendingPayment).filter(PendingPayment.user_id == user_id,
                                                       PendingPayment.reference == parsed["reference"]).first()
            if existing:
                when = existing.created_at.strftime("%-d %b") if existing.created_at else ""
                detail = f"Already captured: {existing.reference} ({existing.status} {when})".strip()
                return status.HTTP_409_CONFLICT, {"added": False, "detail": detail, "message": detail}
        payment = PendingPayment(user_id=user_id, source=data.source, kind=parsed["kind"],
                                 raw_text=data.raw[:2000], amount=parsed["amount"], fee=parsed["fee"],
                                 payee=parsed["payee"], account=parsed["account"], reference=parsed["reference"],
                                 paid_on=parsed["paid_on"], status="pending")
        db.add(payment)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return status.HTTP_409_CONFLICT, {"added": False, "detail": "Already captured",
                                              "message": "Already captured"}
        db.refresh(payment)
        duplicate = PaymentService.possible_duplicate(db, payment)
        return status.HTTP_201_CREATED, {"added": True, "payment": PaymentService.out(payment, duplicate=duplicate),
                                         "message": _capture_message(payment, duplicate)}

    @staticmethod
    def _budget_categories(db: Session, user_id: int, budget_id: Optional[int]) -> dict:
        """{category_id: name} for the expense categories of a budget (empty for savings budgets)."""
        if budget_id is None:
            return {}
        budget = BudgetService.get_budget_by_id(db=db, budget_id=budget_id, user_id=user_id)
        if not budget:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not Found")
        rows = (db.query(Category).join(Allocation, Allocation.category_id == Category.id)
                .filter(Allocation.budget_id == budget.id, Category.user_id == user_id,
                        Category.type == "expense").all())
        return {c.id: c.name for c in rows}

    @staticmethod
    def suggest(db: Session, user_id: int, payee: Optional[str], categories: dict) -> Optional[int]:
        """A remembered payee first, then keywords; only categories in the active budget."""
        if not payee or not categories:
            return None
        rule = db.query(PayeeRule).filter(PayeeRule.user_id == user_id,
                                          PayeeRule.payee == _payee_key(payee)).first()
        if rule and rule.category_id in categories:
            return rule.category_id
        by_name = {name.lower(): cid for cid, name in categories.items()}
        for pattern, name in KEYWORDS:
            if pattern.search(payee) and name.lower() in by_name:
                return by_name[name.lower()]
        return None

    @staticmethod
    def suggest_recurring(db: Session, user_id: int, p: PendingPayment, items: list) -> Optional[int]:
        """A payee remembered as a recurring item first, then the one active item with the same amount."""
        if p.amount is None or not items:
            return None
        ids = {i.id for i in items}
        if p.payee:
            rule = db.query(PayeeRule).filter(PayeeRule.user_id == user_id,
                                              PayeeRule.payee == _payee_key(p.payee)).first()
            if rule and rule.recurring_id in ids:
                return rule.recurring_id
        amount = _money(p.amount)
        matches = [i.id for i in items if _money(i.amount) == amount]
        return matches[0] if len(matches) == 1 else None

    @staticmethod
    def list_pending(db: Session, user_id: int, budget_id: Optional[int]) -> dict:
        """The inbox is every pending payment; only the suggestions follow the active budget."""
        categories = PaymentService._budget_categories(db, user_id, budget_id)
        items = ([i for i in RecurringService._in_budget(db, user_id, budget_id) if not i.paused]
                 if budget_id is not None else [])
        pending = (db.query(PendingPayment).filter(PendingPayment.user_id == user_id,
                                                   PendingPayment.status == "pending")
                   .order_by(PendingPayment.received_at.desc(), PendingPayment.id.desc()).all())
        # Bank messages go to savings, whichever budget is active.
        savings = PaymentService._savings_categories(db, user_id)
        budgets = (db.query(Budget).filter(Budget.user_id == user_id, Budget.type == "savings")
                   .order_by(Budget.name).all())

        def out(p):
            duplicate = PaymentService.possible_duplicate(db, p)
            if SAVINGS.get(p.kind) == "deposit":
                return PaymentService.out(p, duplicate=duplicate,
                                          suggested_budget=budgets[0].id if len(budgets) == 1 else None)
            if p.kind in SAVINGS:
                return PaymentService.out(p, PaymentService._suggest_savings(db, user_id, p, savings), duplicate)
            return PaymentService.out(p, PaymentService.suggest(db, user_id, p.payee, categories), duplicate,
                                      PaymentService.suggest_recurring(db, user_id, p, items))
        return {"payments": [out(p) for p in pending],
                "savings_categories": [{"id": c.id, "name": c.name, "budget_name": budget_name,
                                        "available": _money(available)}
                                       for c, budget_name, available in savings],
                "savings_budgets": [{"id": b.id, "name": b.name, "amount": _money(b.amount)} for b in budgets],
                "categories": [{"id": cid, "name": name} for cid, name in sorted(categories.items(), key=lambda x: x[1].lower())],
                "recurring": [{"id": i.id, "name": i.name, "amount": _money(i.amount), "category_id": i.category_id,
                               "category_name": categories.get(i.category_id, "")}
                              for i in sorted(items, key=lambda i: i.name.lower())]}

    @staticmethod
    def _savings_categories(db: Session, user_id: int) -> list:
        """(category, budget name, allocated amount) for every savings category in a savings budget."""
        return (db.query(Category, Budget.name, Allocation.allocated_amount)
                .join(Allocation, Allocation.category_id == Category.id)
                .join(Budget, Budget.id == Allocation.budget_id)
                .filter(Category.user_id == user_id, Category.type == "savings",
                        Budget.user_id == user_id, Budget.type == "savings")
                .order_by(Budget.name, Category.name).all())

    @staticmethod
    def _rule_key(p: PendingPayment) -> Optional[str]:
        """Card purchases are remembered by card (the merchant changes), transfers by bank."""
        return p.account if p.kind == "card" else p.payee

    @staticmethod
    def _suggest_savings(db: Session, user_id: int, p: PendingPayment, savings: list) -> Optional[int]:
        key = PaymentService._rule_key(p)
        if not key:
            return None
        rule = db.query(PayeeRule).filter(PayeeRule.user_id == user_id, PayeeRule.payee == _payee_key(key)).first()
        return rule.category_id if rule and rule.category_id in {c.id for c, _, _ in savings} else None

    @staticmethod
    def count_pending(db: Session, user_id: int) -> int:
        return db.query(PendingPayment).filter(PendingPayment.user_id == user_id,
                                               PendingPayment.status == "pending").count()

    @staticmethod
    def _forget_raw(payment: PendingPayment):
        if not settings.KEEP_RAW_MESSAGES:
            payment.raw_text = None

    @staticmethod
    def approve(db: Session, user_id: int, payment_id: int, data: ApproveIn) -> dict:
        payment = PaymentService._get(db, user_id, payment_id)
        if payment.status != "pending":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This payment was already handled")
        PaymentService._not_savings(payment)
        category = CategoryService.get_category_by_id(db=db, category_id=data.category_id, user_id=user_id)
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not Found")
        if category.type != "expense":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose an expense category")
        amount = data.amount
        if amount is None:
            if payment.amount is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Enter the amount")
            amount = Decimal(str(payment.amount))
        month = (payment.paid_on or today()).strftime("%Y-%m")
        now = datetime.utcnow()
        expense = Expense(user_id=user_id, category_id=category.id, amount=amount,
                          description=payment.payee or "Payment", month=month, type="spend",
                          created_at=now, updated_at=now)
        db.add(expense)
        db.flush()
        # The fee left the account too (owner decision), as its own expense in "M-Pesa fees".
        fee = FeeService.add_fee(db, user_id, payment.fee, month, payment.payee, category.id)
        payment.status, payment.expense_id = "approved", expense.id
        payment.fee_expense_id = fee.id if fee else None
        PaymentService._forget_raw(payment)
        if data.remember and payment.payee:
            PaymentService._remember(db, user_id, payment.payee, category.id, None)
        db.commit()
        return {"expense_id": expense.id, "amount": _money(amount), "fee": _money(fee.amount) if fee else None,
                "month": month, "category_name": category.name, "fee_category": FEE_CATEGORY}

    @staticmethod
    def _not_savings(payment: PendingPayment):
        if payment.kind in SAVINGS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="This is a bank message. File it to savings.")

    @staticmethod
    def file_savings(db: Session, user_id: int, payment_id: int, data: SavingsIn) -> dict:
        """A withdrawal lowers the savings budget and the category's allocation (as a withdrawal
        entered by hand does); a deposit raises the savings budget's amount."""
        payment = PaymentService._get(db, user_id, payment_id)
        if payment.status != "pending":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This payment was already handled")
        action = SAVINGS.get(payment.kind)
        if action is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="This is not a bank message. Approve it as a payment.")
        amount = data.amount
        if amount is None:
            if payment.amount is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Enter the amount")
            amount = Decimal(str(payment.amount))
        if action == "deposit":
            if data.budget_id is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose a savings budget")
            budget = BudgetService.get_budget_by_id(db=db, budget_id=data.budget_id, user_id=user_id)
            if not budget:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not Found")
            if budget.type != "savings":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose a savings budget")
            budget.amount = Decimal(str(budget.amount)) + amount
            # Undo takes off what was added, so keep it.
            payment.amount, payment.budget_id = amount, budget.id
            message = f"Added {_ksh(amount)} to {budget.name}"
        else:
            if data.category_id is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose a savings category")
            category = CategoryService.get_category_by_id(db=db, category_id=data.category_id, user_id=user_id)
            if not category:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not Found")
            if category.type != "savings":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose a savings category")
            allocation = PaymentService._savings_allocation(db, user_id, category.id)
            if not allocation:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f"{category.name} is not in a savings budget")
            budget = allocation.budget
            if Decimal(str(allocation.allocated_amount)) < amount:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f"{category.name} has only {_ksh(allocation.allocated_amount)}")
            if Decimal(str(budget.amount)) < amount:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f"{budget.name} has only {_ksh(budget.amount)}")
            now = datetime.utcnow()
            expense = Expense(user_id=user_id, category_id=category.id, amount=amount,
                              description=payment.payee or payment.account or "Bank withdrawal",
                              month=(payment.paid_on or today()).strftime("%Y-%m"), type="withdrawal",
                              created_at=now, updated_at=now)
            db.add(expense)
            db.flush()
            budget.amount = Decimal(str(budget.amount)) - amount
            allocation.allocated_amount = Decimal(str(allocation.allocated_amount)) - amount
            payment.expense_id = expense.id
            key = PaymentService._rule_key(payment)
            if data.remember and key:
                PaymentService._remember(db, user_id, key, category.id, None)
            message = f"Withdrew {_ksh(amount)} from {category.name}"
        payment.status = "approved"
        PaymentService._forget_raw(payment)
        db.commit()
        return {"message": message + "."}

    @staticmethod
    def _savings_allocation(db: Session, user_id: int, category_id: int) -> Optional[Allocation]:
        return (db.query(Allocation).join(Budget, Allocation.budget_id == Budget.id)
                .filter(Allocation.category_id == category_id, Budget.user_id == user_id,
                        Budget.type == "savings").first())

    @staticmethod
    def _undo_savings(db: Session, user_id: int, payment: PendingPayment):
        """Put back what file_savings changed: the balances, and the withdrawal itself."""
        if payment.budget_id is not None:
            budget = BudgetService.get_budget_by_id(db=db, budget_id=payment.budget_id, user_id=user_id)
            amount = Decimal(str(payment.amount or 0))
            if budget:
                if Decimal(str(budget.amount)) < amount:
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                        detail=f"{budget.name} has only {_ksh(budget.amount)} left, "
                                               "so this deposit cannot be taken off")
                budget.amount = Decimal(str(budget.amount)) - amount
            payment.budget_id = None
        expense = (db.query(Expense).filter(Expense.id == payment.expense_id, Expense.user_id == user_id).first()
                   if payment.expense_id else None)
        if expense:
            allocation = PaymentService._savings_allocation(db, user_id, expense.category_id)
            if allocation:
                allocation.budget.amount = Decimal(str(allocation.budget.amount)) + Decimal(str(expense.amount))
                allocation.allocated_amount = Decimal(str(allocation.allocated_amount)) + Decimal(str(expense.amount))
            db.delete(expense)
        payment.status, payment.expense_id = "pending", None
        db.commit()

    @staticmethod
    def _remember(db: Session, user_id: int, payee: str, category_id: int, recurring_id: Optional[int]):
        key = _payee_key(payee)
        rule = db.query(PayeeRule).filter(PayeeRule.user_id == user_id, PayeeRule.payee == key).first()
        if rule:
            rule.category_id, rule.recurring_id = category_id, recurring_id
        else:
            db.add(PayeeRule(user_id=user_id, payee=key, category_id=category_id, recurring_id=recurring_id))

    @staticmethod
    def file_recurring(db: Session, user_id: int, payment_id: int, data: RecurringIn) -> dict:
        """File a captured payment as this month's payment of a recurring item (docs/design/payments.md)."""
        payment = PaymentService._get(db, user_id, payment_id)
        if payment.status != "pending":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This payment was already handled")
        PaymentService._not_savings(payment)
        if payment.amount is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="This message has no amount. Approve it as a normal payment.")
        paid = payment.paid_on or today()
        amount = Decimal(str(payment.amount))
        if data.new:
            category = RecurringService._check_category(db, user_id, data.new.category_id)
            fee = Decimal(str(payment.fee or 0))
            item = RecurringExpense(user_id=user_id, category_id=category.id, name=data.new.name.strip(),
                                    amount=amount, anchor_day=paid.day, next_due=paid, mode=data.new.mode,
                                    paused=False, usual_fee=fee if fee > 0 else None)
            db.add(item)
            db.flush()
        else:
            item = RecurringService._get(db, user_id, data.recurring_id)
            if item.paused:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                    detail=f"{item.name} is paused. Resume it in Recurring first.")
        due = month_day(paid.year, paid.month, item.anchor_day)
        label = _month_label(due)
        month = due.strftime("%Y-%m")
        run = db.query(RecurringRun).filter(RecurringRun.recurring_id == item.id, RecurringRun.due_date == due).first()
        if run is None:
            if due != item.next_due:
                if due > item.next_due:
                    detail = (f"{item.name} still has {_month_label(item.next_due)} to record or skip. "
                              "Do that in Recurring first, or approve this as a normal payment.")
                else:
                    detail = (f"{item.name} starts in {_month_label(item.next_due)}. "
                              "Approve this as a normal payment.")
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
            run = RecurringService._record(db, item, due, "approved", amount=amount, usual_fee=False, commit=False)
            fee = FeeService.add_fee(db, user_id, payment.fee, month, payment.payee or item.name, item.category_id)
            payment.expense_id, payment.recurring_run_id = run.expense_id, run.id
            payment.fee_expense_id = fee.id if fee else None
            message = f"Recorded {item.name} for {label}: {_ksh(amount)}"
        elif run.action == "skipped":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"{item.name} was skipped for {label}. Undo the skip in Recurring first, "
                                       "or approve this as a normal payment.")
        else:
            # Already recorded (auto, or approved earlier): keep that expense and add only the fee.
            fee = None
            real_fee = Decimal(str(payment.fee or 0))
            usual = (db.query(Expense).filter(Expense.id == run.fee_expense_id, Expense.user_id == user_id).first()
                     if run.fee_expense_id else None)
            if usual and real_fee > 0:
                # The real fee replaces the usual one; Undo puts the usual amount back.
                payment.previous_fee, usual.amount = usual.amount, real_fee
                payment.fee_expense_id, fee = usual.id, usual
            elif not usual:
                fee = FeeService.add_fee(db, user_id, payment.fee, month, payment.payee or item.name, item.category_id)
                payment.fee_expense_id = fee.id if fee else None
            message = f"{item.name} for {label} was already recorded"
            message += ", so only the fee was added" if fee else ", so nothing new was added"
            if run.amount is not None and _money(run.amount) != _money(amount):
                message += f". It was recorded as {_ksh(run.amount)}; this message says {_ksh(amount)}"
        if fee:
            message += f" + {_ksh(fee.amount)} to {FEE_CATEGORY}"
        payment.status = "approved"
        PaymentService._forget_raw(payment)
        if data.remember and payment.payee:
            PaymentService._remember(db, user_id, payment.payee, item.category_id, item.id)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already recorded")
        return {"recurring_id": item.id, "month": month, "message": message + "."}

    @staticmethod
    def dismiss(db: Session, user_id: int, payment_id: int):
        payment = PaymentService._get(db, user_id, payment_id)
        if payment.status != "pending":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This payment was already handled")
        payment.status = "dismissed"
        PaymentService._forget_raw(payment)
        db.commit()

    @staticmethod
    def restore(db: Session, user_id: int, payment_id: int):
        """Undo: back to the inbox. What the approval added is removed (the expense, the fee, and a
        recurring run it recorded); a usual fee it replaced gets its amount back. The original
        text stays cleared."""
        payment = PaymentService._get(db, user_id, payment_id)
        if payment.kind in SAVINGS:
            return PaymentService._undo_savings(db, user_id, payment)

        def expense(expense_id):
            return (db.query(Expense).filter(Expense.id == expense_id, Expense.user_id == user_id).first()
                    if expense_id else None)

        run = (db.query(RecurringRun).filter(RecurringRun.id == payment.recurring_run_id,
                                             RecurringRun.user_id == user_id).first()
               if payment.recurring_run_id else None)
        if run:
            item = db.query(RecurringExpense).filter(RecurringExpense.id == run.recurring_id).first()
            RecurringService._remove_run(db, user_id, item, run)
        elif expense(payment.expense_id):
            db.delete(expense(payment.expense_id))
        fee = expense(payment.fee_expense_id)
        if fee is not None and payment.previous_fee is not None:
            fee.amount = payment.previous_fee
        elif fee is not None:
            db.delete(fee)
        payment.status, payment.expense_id, payment.fee_expense_id = "pending", None, None
        payment.previous_fee, payment.recurring_run_id = None, None
        db.commit()
