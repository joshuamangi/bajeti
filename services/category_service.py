import logging
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from data.db.models.models import Allocation, Category, Expense, Transfer
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
    def get_categories_with_stats(db: Session, user_id: int):
        current_year_month = datetime.utcnow().strftime("%Y-%m")
        categories = db.query(Category).filter(
            Category.user_id == user_id,
            Category.type == "expense").all()
        result = []

        for category in categories:
            expenses = db.query(Expense).filter(
                Expense.user_id == user_id,
                Expense.category_id == category.id,
                Expense.month == current_year_month,
                Expense.type == "spend"
            ).all()

            total_spend = sum(Decimal(str(exp.amount)) for exp in expenses)
            expense_count = len(expenses)

            # transfers (incoming and outgoing)
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

            def get_cat_name(db, category_id):
                if not category_id:
                    return None
                cat = db.query(Category).filter(
                    Category.id == category_id).first()
                return cat.name if cat else None

            total_incoming = sum(Decimal(str(t.amount)) for t in incoming)
            total_outgoing = sum(Decimal(str(t.amount)) for t in outgoing)

            # convert transfers into simple dicts for the UI
            incoming_list = [
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
                    "from_category_name": get_cat_name(db, t.from_category_id),
                    "to_category_name": get_cat_name(db, t.to_category_id),
                }
                for t in incoming
            ]

            outgoing_list = [
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
                    "from_category_name": get_cat_name(db, t.from_category_id),
                    "to_category_name": get_cat_name(db, t.to_category_id),
                }
                for t in outgoing
            ]

            # net top-ups applied to the category for the month
            net_topup = total_incoming - total_outgoing

            # balance = (limit + net_topup) - used
            allocation = db.query(Allocation).filter(
                Allocation.category_id == category.id
            ).first()

            allocated_amount = (
                Decimal(str(allocation.allocated_amount))
                if allocation else Decimal("0")
            )
            balance = (allocated_amount + net_topup) - total_spend

            # convert expenses to dicts (same as before)
            expenses_list = [
                {
                    "id": exp.id,
                    "amount": float(exp.amount),
                    "month": exp.month,
                    "description": exp.description,
                    "category_id": exp.category_id,
                    "user_id": exp.user_id,
                    "type": exp.type,
                    "created_at": exp.created_at,
                    "updated_at": exp.updated_at,
                }
                for exp in expenses
            ]

            result.append({
                "id": category.id,
                "name": category.name,
                "allocated_amount": float(allocated_amount),
                "user_id": category.user_id,
                "type": category.type,
                "created_at": category.created_at,
                "updated_at": category.updated_at,
                "expense_count": expense_count,
                "balance": float(balance),
                "expenses": expenses_list,
                "used": float(total_spend),
                "transfers_in": incoming_list,
                "transfers_out": outgoing_list,
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
