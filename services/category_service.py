import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session

from data.db.models.models import Allocation, Budget, Category, Expense, Transfer
from schema.category import CategoryBase

logger = logging.getLogger(__name__)


class CategoryService:

    @staticmethod
    def get_all_categories(db: Session, user_id: int):
        categories = db.query(Category).filter(
            Category.user_id == user_id
        ).all()
        return categories

    @staticmethod
    def get_categories_by_type(db: Session, user_id: int, category_type: str):

        # 1️⃣ Get all budgets of this type for the user
        budgets = db.query(Budget.id).filter(
            Budget.user_id == user_id,
            Budget.type == category_type
        ).all()

        budget_ids = [b.id for b in budgets]

        # If no budgets exist → nothing is allocated → return all categories
        if not budget_ids:
            return db.query(Category).filter(
                Category.user_id == user_id,
                Category.type == category_type
            ).all()

        # 2️⃣ Get all allocated category_ids for those budgets
        allocated_category_ids = db.query(Allocation.category_id).filter(
            Allocation.budget_id.in_(budget_ids)
        ).all()

        allocated_category_ids = [
            a.category_id for a in allocated_category_ids]

        # 3️⃣ Return categories NOT already allocated
        available_categories = db.query(Category).filter(
            Category.user_id == user_id,
            Category.type == category_type,
            ~Category.id.in_(allocated_category_ids)  # NOT IN
        ).all()

        return available_categories

    @staticmethod
    def get_categories_with_stats(
        db: Session,
        user_id: int,
        budget_id: int,
        month: Optional[str] = None
    ):
        current_month = month or datetime.utcnow().strftime("%Y-%m")

        # Get budget
        budget = db.query(Budget).filter(
            Budget.id == budget_id,
            Budget.user_id == user_id
        ).first()

        if not budget:
            return []

        category_type = budget.type  # expense OR savings
        expense_type = "spend" if category_type == "expense" else "withdrawal"

        # Get allocations for this budget ONCE
        allocations = db.query(Allocation).filter(
            Allocation.budget_id == budget_id
        ).all()

        # Build quick lookup {category_id: allocation}
        allocation_map = {
            alloc.category_id: alloc
            for alloc in allocations
        }

        allocated_category_ids = list(allocation_map.keys())

        if not allocated_category_ids:
            return []

        categories = db.query(Category).filter(
            Category.user_id == user_id,
            Category.type == category_type,
            Category.id.in_(allocated_category_ids)
        ).all()

        result = []

        def get_cat_name(category_id):
            if not category_id:
                return None
            cat = db.query(Category).filter(
                Category.id == category_id
            ).first()
            return cat.name if cat else None

        for category in categories:

            # Expenses (spend OR withdrawal depending on budget type)
            expenses = db.query(Expense).filter(
                Expense.user_id == user_id,
                Expense.category_id == category.id,
                Expense.month == current_month,
                Expense.type == expense_type
            ).all()

            total_used = sum(Decimal(str(e.amount)) for e in expenses)

            # Transfers
            incoming = db.query(Transfer).filter(
                Transfer.user_id == user_id,
                Transfer.to_category_id == category.id,
                Transfer.month == current_month
            ).all()

            outgoing = db.query(Transfer).filter(
                Transfer.user_id == user_id,
                Transfer.from_category_id == category.id,
                Transfer.month == current_month
            ).all()

            total_incoming = sum(Decimal(str(t.amount)) for t in incoming)
            total_outgoing = sum(Decimal(str(t.amount)) for t in outgoing)
            net_transfers = total_incoming - total_outgoing

            # Allocation lookup (NO extra query)
            allocation = allocation_map.get(category.id)
            allocated_amount = (
                Decimal(str(allocation.allocated_amount))
                if allocation else Decimal("0")
            )

            balance = (allocated_amount + net_transfers) - total_used

            result.append({
                "id": category.id,
                "name": category.name,
                "allocated_amount": float(allocated_amount),
                "user_id": category.user_id,
                "type": category.type,
                "created_at": category.created_at,
                "updated_at": category.updated_at,
                "expense_count": len(expenses),
                "balance": float(balance),
                "expenses": [
                    {
                        "id": e.id,
                        "amount": float(e.amount),
                        "month": e.month,
                        "description": e.description,
                        "category_id": e.category_id,
                        "user_id": e.user_id,
                        "type": e.type,
                        "created_at": e.created_at,
                        "updated_at": e.updated_at,
                    }
                    for e in expenses
                ],
                "used": float(total_used),
                "transfers_in": [
                    {
                        "id": t.id,
                        "user_id": t.user_id,
                        "created_at": t.created_at,
                        "updated_at": t.updated_at,
                        "amount": float(t.amount),
                        "description": t.description,
                        "month": t.month,
                        "from_category_id": t.from_category_id,
                        "to_category_id": t.to_category_id,
                        "from_category_name": get_cat_name(t.from_category_id),
                        "to_category_name": get_cat_name(t.to_category_id),
                    }
                    for t in incoming
                ],
                "transfers_out": [
                    {
                        "id": t.id,
                        "user_id": t.user_id,
                        "created_at": t.created_at,
                        "updated_at": t.updated_at,
                        "amount": float(t.amount),
                        "description": t.description,
                        "month": t.month,
                        "from_category_id": t.from_category_id,
                        "to_category_id": t.to_category_id,
                        "from_category_name": get_cat_name(t.from_category_id),
                        "to_category_name": get_cat_name(t.to_category_id),
                    }
                    for t in outgoing
                ],
                "total_transfers_in": float(total_incoming),
                "total_transfers_out": float(total_outgoing),
            })

        return result

    @staticmethod
    def get_category_by_id(db: Session, user_id: int, category_id: int):
        category = db.query(Category).filter(
            Category.id == category_id,
            Category.user_id == user_id,
        ).first()
        return category

    @staticmethod
    def get_existing_category(db: Session, user_id: int, category: CategoryBase):
        existing_category = db.query(Category).filter(
            Category.name == category.name,
            Category.user_id == user_id,
            Category.type == category.type
        ).first()

        return existing_category

    @staticmethod
    def get_savings_categories_with_stats(db: Session, user_id: int):
        current_year_month = datetime.utcnow().strftime("%Y-%m")

        categories = db.query(Category).filter(
            Category.user_id == user_id,
            Category.type == "savings"
        ).all()

        result = []

        for category in categories:
            incoming = db.query(Transfer).filter(
                Transfer.user_id == user_id,
                Transfer.to_category_id == category.id,
                Transfer.month == current_year_month
            ).all()

            outgoing = db.query(Transfer).filter(
                Transfer.user_id == user_id,
                Transfer.from_category_id == category.id,
                Transfer.month == current_year_month
            ).all()

            total_incoming = sum(Decimal(str(t.amount)) for t in incoming)
            total_outgoing = sum(Decimal(str(t.amount)) for t in outgoing)

            allocation = db.query(Allocation).filter(
                Allocation.category_id == category.id
            ).first()

            allocated_amount = (
                Decimal(str(allocation.allocated_amount))
                if allocation else Decimal("0")
            )

            balance = allocated_amount + total_incoming - total_outgoing

            result.append({
                "id": category.id,
                "name": category.name,
                "allocated_amount": float(allocated_amount),
                "balance": float(balance),
                "total_deposits": float(total_incoming),
                "total_withdrawals": float(total_outgoing),
            })

        return result

    @staticmethod
    def save_new_category(db: Session, user_id: int, category: CategoryBase):
        new_category = Category(
            name=category.name,
            type=category.type,
            user_id=user_id
        )
        db.add(new_category)
        db.commit()
        db.refresh(new_category)
        return new_category

    @staticmethod
    def update_category(db: Session, existing_category: Category, update_data: CategoryBase):
        existing_category.name = update_data.name
        existing_category.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(existing_category)
        return existing_category

    @staticmethod
    def delete_category(db: Session, category: Category):
        db.delete(category)
        db.commit()
