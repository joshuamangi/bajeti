
import logging
from typing import Optional
from fastapi import APIRouter, Depends, logger, status

from core.security import get_current_user
from data.db.db import get_db
from schema.allocation import AllocationCreate, AllocationOut
from sqlalchemy.orm import Session

from schema.user import UserOut
from services.allocation_service import AllocationService

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter(
    prefix="/api/budgets/{budget_id}/allocations", tags=["allocations"])
# get


@router.get("/overview", status_code=status.HTTP_200_OK)
def get_budget_overview(
    budget_id: int,
    month: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    return AllocationService.get_budget_overview(
        db=db,
        user_id=current_user.id,
        budget_id=budget_id,
        month=month
    )


@router.post("/", response_model=AllocationOut, status_code=status.HTTP_201_CREATED)
def create_new_allocation(budget_id: int,
                          allocation: AllocationCreate,
                          db: Session = Depends(get_db),
                          current_user: UserOut = Depends(get_current_user)):
    logger.info("Allocation request: category_id=%s, budget_id=%s, amount=%s",
                allocation.category_id, budget_id, allocation.allocated_amount)
    return AllocationService.add_allocation(
        db=db, budget_id=budget_id, user_id=current_user.id, data=allocation)
# put
# delete
