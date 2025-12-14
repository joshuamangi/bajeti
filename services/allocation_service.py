from sqlalchemy.orm import Session

from data.db.models.models import Allocation


class AllocationService:
    @staticmethod
    def check_allocaation_exists(db: Session, budget_id: int, allocation_id: int):
        existing_allocation = db.query(Allocation).filter(
            Allocation.budget_id == budget_id,
            Allocation.id == allocation_id
        ).first()
        return existing_allocation
