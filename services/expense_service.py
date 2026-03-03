from decimal import Decimal
import logging
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import and_

from data.db.models.models import Allocation, Budget, Expense
from schema.expense import ExpenseCreate
from schema.user import UserOut
from fastapi import HTTPException, status


logger = logging.getLogger("app.expenses")


class ExpenseService:
    @staticmethod
    def get_all_expenses(db: Session, current_user: UserOut):
        expenses = db.query(Expense).filter(
            Expense.user_id == current_user.id,
            Expense.type == "spend"
        ).all()

        if not expenses:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No expenses found for this user"
            )

        return expenses

    @staticmethod
    def get_current_month_expense(db: Session, current_user: UserOut):
        current_year_month = datetime.utcnow().strftime("%Y-%m")

        expenses = db.query(Expense).filter(
            and_(
                Expense.month == current_year_month,
                Expense.user_id == current_user.id,
                Expense.type == "spend"
            )
        ).all()

        if not expenses:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No expenses found for {current_year_month}"
            )

        return expenses

    @staticmethod
    def get_expenses_by_month(db: Session, month: str, current_user: UserOut):
        expenses = db.query(Expense).filter(
            and_(
                Expense.month == month,
                Expense.user_id == current_user.id,
                Expense.type == "spend"
            )
        ).all()

        if not expenses:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No expenses found for {month}"
            )

        return expenses

    @staticmethod
    def get_expenses_by_category(db: Session, category_id: int, current_user: UserOut):
        expenses = db.query(Expense).filter(
            and_(
                Expense.category_id == category_id,
                Expense.user_id == current_user.id,
                Expense.type == "spend"
            )
        ).all()

        if not expenses:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No expenses found for category {category_id}"
            )

        return expenses

    @staticmethod
    def get_expenses_by_category_and_month(
        db: Session,
        category_id: int,
        month: str,
        current_user: UserOut
    ):
        expenses = db.query(Expense).filter(
            and_(
                Expense.category_id == category_id,
                Expense.month == month,
                Expense.user_id == current_user.id,
                # Expense.type == "spend"
            )
        ).all()

        if not expenses:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No expenses found for category {category_id} in {month}"
            )

        return expenses

    @staticmethod
    def create_expense(db: Session, expense: ExpenseCreate, current_user: UserOut):
        now = datetime.utcnow()

        new_expense = Expense(
            user_id=current_user.id,
            category_id=expense.category_id,
            amount=expense.amount,
            description=expense.description,
            month=expense.month,
            type=expense.type,
            created_at=now,
            updated_at=now
        )

        db.add(new_expense)
        db.commit()
        db.refresh(new_expense)

        return new_expense

    @staticmethod
    def create_withdrawal(
        db: Session,
        withdrawal: ExpenseCreate,
        current_user: UserOut
    ):
        try:
            # Get Allocation + Budget
            allocation = db.query(Allocation).join(
                Budget,
                Allocation.budget_id == Budget.id
            ).filter(
                Allocation.category_id == withdrawal.category_id,
                Budget.user_id == current_user.id
            ).first()

            if not allocation:
                raise HTTPException(
                    status_code=404,
                    detail="No allocation found for this category"
                )

            budget = allocation.budget
            amount = Decimal(withdrawal.amount)

            if Decimal(budget.amount) < amount:
                raise HTTPException(
                    status_code=400,
                    detail="Insufficient budget balance"
                )

            if Decimal(allocation.allocated_amount) < amount:
                raise HTTPException(
                    status_code=400,
                    detail="Insufficient allocated amount"
                )

            # Create Withdrawal
            now = datetime.utcnow()

            db_withdrawal = Expense(
                user_id=current_user.id,
                category_id=withdrawal.category_id,
                amount=amount,
                description=withdrawal.description,
                month=withdrawal.month,
                type="withdrawal",
                created_at=now,
                updated_at=now
            )

            db.add(db_withdrawal)

            # Reduce Budget + Allocation
            budget.amount = Decimal(budget.amount) - amount
            allocation.allocated_amount = (
                Decimal(allocation.allocated_amount) - amount
            )

            db.commit()
            db.refresh(db_withdrawal)

            return db_withdrawal

        except SQLAlchemyError:
            db.rollback()
            raise

    @staticmethod
    def update_expense(db: Session, expense_id: int, expense: ExpenseCreate, current_user: UserOut):
        db_expense = db.query(Expense).filter(
            and_(
                Expense.id == expense_id,
                Expense.user_id == current_user.id
            )
        ).first()

        if not db_expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expense not found or not yours"
            )

        db_expense.category_id = expense.category_id
        db_expense.amount = expense.amount
        db_expense.description = expense.description
        db_expense.month = expense.month
        db_expense.type = expense.type
        db_expense.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(db_expense)

        return db_expense

    @staticmethod
    def update_withdrawal(
        db: Session,
        expense_id: int,
        withdrawal: ExpenseCreate,
        current_user: UserOut
    ):
        try:
            db_withdrawal = db.query(Expense).filter(
                Expense.id == expense_id,
                Expense.user_id == current_user.id,
                Expense.type == "withdrawal"
            ).first()

            if not db_withdrawal:
                raise HTTPException(404, "Withdrawal not found")

            allocation = db.query(Allocation).join(
                Budget
            ).filter(
                Allocation.category_id == db_withdrawal.category_id,
                Budget.user_id == current_user.id
            ).first()

            if not allocation:
                raise HTTPException(404, "Allocation not found")

            budget = allocation.budget

            old_amount = Decimal(db_withdrawal.amount)
            new_amount = Decimal(withdrawal.amount)
            difference = new_amount - old_amount

            # If increasing withdrawal
            if difference > 0:
                if Decimal(budget.amount) < difference:
                    raise HTTPException(400, "Insufficient budget balance")
                if Decimal(allocation.allocated_amount) < difference:
                    raise HTTPException(400, "Insufficient allocated amount")

            # Adjust Budget + Allocation
            budget.amount = Decimal(budget.amount) - difference
            allocation.allocated_amount = (
                Decimal(allocation.allocated_amount) - difference
            )

            # Update withdrawal
            db_withdrawal.amount = new_amount
            db_withdrawal.description = withdrawal.description
            db_withdrawal.month = withdrawal.month
            db_withdrawal.updated_at = datetime.utcnow()

            db.commit()
            db.refresh(db_withdrawal)

            return db_withdrawal

        except SQLAlchemyError:
            db.rollback()
            raise

    @staticmethod
    def delete_expense(db: Session, expense_id: int, current_user: UserOut):
        db_expense = db.query(Expense).filter(
            and_(
                Expense.id == expense_id,
                Expense.user_id == current_user.id
            )
        ).first()

        if not db_expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expense not found or not yours"
            )

        db.delete(db_expense)
        db.commit()

    @staticmethod
    def delete_withdrawal(
        db: Session,
        expense_id: int,
        current_user: UserOut
    ):
        try:
            db_withdrawal = db.query(Expense).filter(
                Expense.id == expense_id,
                Expense.user_id == current_user.id,
                Expense.type == "withdrawal"
            ).first()

            if not db_withdrawal:
                raise HTTPException(404, "Withdrawal not found")

            allocation = db.query(Allocation).join(
                Budget
            ).filter(
                Allocation.category_id == db_withdrawal.category_id,
                Budget.user_id == current_user.id
            ).first()

            if not allocation:
                raise HTTPException(404, "Allocation not found")

            budget = allocation.budget
            amount = Decimal(db_withdrawal.amount)

            # Restore values
            budget.amount = Decimal(budget.amount) + amount
            allocation.allocated_amount = (
                Decimal(allocation.allocated_amount) + amount
            )

            db.delete(db_withdrawal)
            db.commit()

            return {"detail": "Withdrawal deleted successfully"}

        except SQLAlchemyError:
            db.rollback()
            raise
