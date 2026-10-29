import re
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from data.db.models.models import Allocation, Category, Expense, PayeeRule, PendingPayment
from schema.payment import ApproveIn, CaptureIn
from services.budget_service import BudgetService
from services.category_service import CategoryService
from services.payment_parser import parse
from services.recurring_service import today

# Payee words -> category name, matched in the active budget (from the prototype).
KEYWORDS = [
    (re.compile(r"grocer|supermarket|mart|market|duka", re.I), "Groceries"),
    (re.compile(r"pharm|clinic|hospital|chemist", re.I), "Health"),
    (re.compile(r"fuel|petrol|shell|rubis|matatu|taxi", re.I), "Transport"),
    (re.compile(r"power|water|internet|fibre|wifi", re.I), "Utilities"),
    (re.compile(r"cinema|movie|stream", re.I), "Entertainment"),
]


def _money(value) -> Optional[Decimal]:
    return None if value is None else Decimal(str(value)).quantize(Decimal("0.01"))


def _payee_key(payee: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (payee or "").strip().lower())


class PaymentService:

    @staticmethod
    def _get(db: Session, user_id: int, payment_id: int) -> PendingPayment:
        payment = db.query(PendingPayment).filter(
            PendingPayment.id == payment_id, PendingPayment.user_id == user_id).first()
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        return payment

    @staticmethod
    def out(p: PendingPayment, suggested: Optional[int] = None) -> dict:
        amount, fee = _money(p.amount), _money(p.fee)
        return {
            "id": p.id, "source": p.source, "kind": p.kind, "status": p.status,
            "amount": amount, "fee": fee,
            "total": (amount + (fee or Decimal("0"))) if amount is not None else None,
            "payee": p.payee, "reference": p.reference, "paid_on": p.paid_on,
            "received_at": p.received_at, "raw_text": p.raw_text,
            "suggested_category_id": suggested,
        }

    @staticmethod
    def capture(db: Session, user_id: int, data: CaptureIn) -> tuple:
        """Returns (http status, body). 201 added, 200 ignored with a reason, 409 already captured."""
        parsed = parse(data.raw)
        if parsed.get("ignored"):
            return status.HTTP_200_OK, {"added": False, "kind": parsed["kind"], "reason": parsed["ignored"]}
        if parsed["reference"]:
            existing = db.query(PendingPayment).filter(PendingPayment.user_id == user_id,
                                                       PendingPayment.reference == parsed["reference"]).first()
            if existing:
                when = existing.created_at.strftime("%-d %b") if existing.created_at else ""
                raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                    detail=f"Already captured: {existing.reference} ({existing.status} {when})".strip())
        payment = PendingPayment(user_id=user_id, source=data.source, kind=parsed["kind"],
                                 raw_text=data.raw[:2000], amount=parsed["amount"], fee=parsed["fee"],
                                 payee=parsed["payee"], reference=parsed["reference"],
                                 paid_on=parsed["paid_on"], status="pending")
        db.add(payment)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already captured")
        db.refresh(payment)
        return status.HTTP_201_CREATED, {"added": True, "payment": PaymentService.out(payment)}

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
    def list_pending(db: Session, user_id: int, budget_id: Optional[int]) -> dict:
        """The inbox is every pending payment; only the suggestions follow the active budget."""
        categories = PaymentService._budget_categories(db, user_id, budget_id)
        pending = (db.query(PendingPayment).filter(PendingPayment.user_id == user_id,
                                                   PendingPayment.status == "pending")
                   .order_by(PendingPayment.received_at.desc(), PendingPayment.id.desc()).all())
        return {"payments": [PaymentService.out(p, PaymentService.suggest(db, user_id, p.payee, categories))
                             for p in pending],
                "categories": [{"id": cid, "name": name} for cid, name in sorted(categories.items(), key=lambda x: x[1].lower())]}

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
        category = CategoryService.get_category_by_id(db=db, category_id=data.category_id, user_id=user_id)
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not Found")
        if category.type != "expense":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose an expense category")
        amount = data.amount
        if amount is None:
            if payment.amount is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Enter the amount")
            # The fee left the account too, so it counts (owner decision).
            amount = Decimal(str(payment.amount)) + Decimal(str(payment.fee or 0))
        month = (payment.paid_on or today()).strftime("%Y-%m")
        now = datetime.utcnow()
        expense = Expense(user_id=user_id, category_id=category.id, amount=amount,
                          description=payment.payee or "Payment", month=month, type="spend",
                          created_at=now, updated_at=now)
        db.add(expense)
        db.flush()
        payment.status, payment.expense_id = "approved", expense.id
        PaymentService._forget_raw(payment)
        if data.remember and payment.payee:
            key = _payee_key(payment.payee)
            rule = db.query(PayeeRule).filter(PayeeRule.user_id == user_id, PayeeRule.payee == key).first()
            if rule:
                rule.category_id = category.id
            else:
                db.add(PayeeRule(user_id=user_id, payee=key, category_id=category.id))
        db.commit()
        return {"expense_id": expense.id, "amount": _money(amount), "month": month}

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
        """Undo: back to the inbox. An approval's expense is removed. The original text stays cleared."""
        payment = PaymentService._get(db, user_id, payment_id)
        if payment.expense_id:
            expense = db.query(Expense).filter(Expense.id == payment.expense_id, Expense.user_id == user_id).first()
            if expense:
                db.delete(expense)
        payment.status, payment.expense_id = "pending", None
        db.commit()
