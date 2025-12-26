from datetime import datetime
from sqlalchemy import desc
from sqlalchemy.orm import Session

from data.db.models.models import Budget
from schema.budget import BudgetBase


class BudgetService:
    @staticmethod
    def check_budget_exists(db: Session, user_id: int, budget: BudgetBase):
        # query to add budget
        existing_budget = db.query(Budget).filter(
            Budget.name == budget.name,
            Budget.user_id == user_id
        ).first()

        return existing_budget

    @staticmethod
    def fetch_current_budget(db: Session, user_id: int):
        # 1️⃣ Try to find the 'Monthly' budget
        monthly_budget = db.query(Budget).filter(
            Budget.user_id == user_id,
            Budget.name == "Monthly"
        ).first()

        if monthly_budget:
            return monthly_budget

        # 2️⃣ Otherwise return the most recently created one
        return (
            db.query(Budget)
            .filter(Budget.user_id == user_id)
            .order_by(desc(Budget.created_at))
            .first()
        )

    @staticmethod
    def save_new_budget(db: Session, user_id: int, budget: BudgetBase):
        new_budget = Budget(
            name=budget.name,
            amount=budget.amount,
            user_id=user_id
        )
        db.add(new_budget)
        db.commit()
        db.refresh(new_budget)
        return new_budget

    @staticmethod
    def get_all_budgets(db: Session, user_id: int):
        budgets = db.query(Budget).filter(
            Budget.user_id == user_id
        ).all()
        return budgets

    @staticmethod
    def get_budget_by_id(db: Session, user_id: int, budget_id: int):
        budget = db.query(Budget).filter(
            Budget.user_id == user_id,
            Budget.id == budget_id
        ).first()
        return budget

    @staticmethod
    def update_budget(db: Session, existing_budget: Budget, updated_budget: BudgetBase):
        existing_budget.name = updated_budget.name
        existing_budget.amount = updated_budget.amount
        existing_budget.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(existing_budget)
        return existing_budget

    @staticmethod
    def remove_budget(db: Session, budget: Budget):
        db.delete(budget)
        db.commit()
