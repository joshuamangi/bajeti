from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from data.db.models.models import Allocation, Category, Expense

# Every M-Pesa fee is its own expense in this category (docs/design/payments.md). Found by name, so
# if it is renamed, the next fee creates a new "M-Pesa fees" category.
FEE_CATEGORY = "M-Pesa fees"


class FeeService:

    @staticmethod
    def _fee_category(db: Session, user_id: int) -> Category:
        category = db.query(Category).filter(Category.user_id == user_id, Category.type == "expense",
                                             func.lower(Category.name) == FEE_CATEGORY.lower()).first()
        if not category:
            category = Category(name=FEE_CATEGORY, type="expense", user_id=user_id)
            db.add(category)
            db.flush()
        return category

    @staticmethod
    def _allocate_beside(db: Session, fee_category: Category, paid_category_id: int):
        """Put the fee category in every budget that holds the paid category, at 0, so the fee shows
        where the payment does. The owner sets an allowance later."""
        budget_ids = [a.budget_id for a in db.query(Allocation).filter(Allocation.category_id == paid_category_id)]
        have = {a.budget_id for a in db.query(Allocation).filter(Allocation.category_id == fee_category.id)}
        for budget_id in budget_ids:
            if budget_id not in have:
                db.add(Allocation(budget_id=budget_id, category_id=fee_category.id, allocated_amount=0))

    @staticmethod
    def add_fee(db: Session, user_id: int, fee, month: str, payee: Optional[str],
                paid_category_id: int) -> Optional[Expense]:
        """Add the fee as its own expense (no commit). None when there is no fee."""
        amount = Decimal(str(fee or 0))
        if amount <= 0:
            return None
        category = FeeService._fee_category(db, user_id)
        FeeService._allocate_beside(db, category, paid_category_id)
        now = datetime.utcnow()
        expense = Expense(user_id=user_id, category_id=category.id, amount=amount,
                          description=f"Fee: {payee}" if payee else "M-Pesa fee", month=month, type="spend",
                          created_at=now, updated_at=now)
        db.add(expense)
        db.flush()
        return expense
