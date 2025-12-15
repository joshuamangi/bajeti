from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from data.db.models.models import Allocation
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
    def get_allocation_by_id(db: Session, budget_id: int, allocation_id: int):
        allocation = db.query(Allocation).filter(
            Allocation.budget_id == budget_id,
            Allocation.id == allocation_id
        ).first()
        return allocation

    @staticmethod
    def fetch_all_allocations(db: Session, budget_id: int):
        allocations = db.query(Allocation).filter(
            Allocation.budget_id == budget_id
        ).all()

        return allocations

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
    def update_allocation(db: Session, allocation: AllocationCreate, existing_allocation: Allocation):
        existing_allocation.allocated_amount = allocation.allocated_amount
        existing_allocation.category_id = allocation.category_id
        existing_allocation.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(existing_allocation)
        return existing_allocation

    @staticmethod
    def remove_allocation(db: Session, allocation: Allocation):
        db.delete(allocation)
        db.commit()
