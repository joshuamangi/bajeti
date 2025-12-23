from datetime import datetime
from decimal import Decimal
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from data.db.models.models import Allocation, Budget, Category, Expense
from schema.allocation import AllocationCreate
from services.budget_service import BudgetService
from services.category_service import CategoryService


class AllocationService:
    @staticmethod
    def check_allocation_exists(db: Session, budget_id: int, category_id: int):
        existing_allocation = db.query(Allocation).filter(
            Allocation.budget_id == budget_id,
            Allocation.category_id == category_id
        ).first()
        return existing_allocation

    @staticmethod
    def add_allocation(db: Session, user_id: int, budget_id: int, data: AllocationCreate):
        existing_budget = BudgetService.get_budget_by_id(db=db,
                                                         budget_id=budget_id, user_id=user_id)

        if not existing_budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Budget not Found")

        existing_category = CategoryService.get_category_by_id(
            db=db, category_id=data.category_id, user_id=user_id)

        if not existing_category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Category not Found")

        existing_allocation = AllocationService.check_allocation_exists(db=db,
                                                                        budget_id=budget_id, category_id=data.category_id)

        if existing_allocation:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Category already allocated in this budget")

        allocation = Allocation(
            budget_id=budget_id,
            category_id=data.category_id,
            allocated_amount=data.allocated_amount
        )

        db.add(allocation)
        db.commit()
        db.refresh(allocation)
        return allocation

    @staticmethod
    def get_budget_overview(
        db: Session,
        user_id: int,
        budget_id: int,
        month: Optional[str] = None
    ):
        if not month:
            month = datetime.utcnow().strftime("%Y-%m")

        # 1. Budget
        budget = db.query(Budget).filter(
            Budget.id == budget_id,
            Budget.user_id == user_id
        ).first()

        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found"
            )

        # 2. Allocations + Categories
        allocations = (
            db.query(Allocation, Category)
            .join(Category, Category.id == Allocation.category_id)
            .filter(
                Allocation.budget_id == budget_id,
                Category.user_id == user_id,
                Category.type == "expense"
            )
            .all()
        )

        allocation_rows = []
        total_allocated = Decimal("0")
        total_spent = Decimal("0")

        for allocation, category in allocations:
            allocated_amount = Decimal(str(allocation.allocated_amount))
            total_allocated += allocated_amount

            # 3. Expenses per category (month + spend)
            spent = (
                db.query(func.coalesce(func.sum(Expense.amount), 0))
                .filter(
                    Expense.user_id == user_id,
                    Expense.category_id == category.id,
                    Expense.month == month,
                    Expense.type == "spend"
                )
                .scalar()
            )

            spent = Decimal(str(spent))
            total_spent += spent

            remaining = allocated_amount - spent
            percent_used = (
                (spent / allocated_amount) * 100
                if allocated_amount > 0 else Decimal("0")
            )

            allocation_rows.append({
                "allocation_id": allocation.id,
                "category_id": category.id,
                "category_name": category.name,
                "allocated_amount": float(allocated_amount),
                "used_amount": float(spent),
                "remaining_amount": float(remaining),
                "percent_used": float(percent_used),
            })

        unallocated = Decimal(str(budget.amount)) - total_allocated
        utilization_percent = (
            (total_spent / Decimal(str(budget.amount))) * 100
            if budget.amount > 0 else Decimal("0")
        )

        return {
            "budget": {
                "id": budget.id,
                "name": budget.name,
                "amount": float(budget.amount),
                "month": month,
            },
            "summary": {
                "total_allocated": float(total_allocated),
                "unallocated": float(unallocated),
                "total_spent": float(total_spent),
                "utilization_percent": float(utilization_percent),
            },
            "allocations": allocation_rows
        }
