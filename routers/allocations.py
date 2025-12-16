
from fastapi import APIRouter, Depends, status

from core.security import get_current_user
from data.db.db import get_db
from schema.allocation import AllocationCreate, AllocationOut
from sqlalchemy.orm import Session

from schema.user import UserOut
from services.allocation_service import AllocationService

router = APIRouter(
    prefix="/api/budgets/{budget_id}/allocations", tags=["allocations"])
# get
# post


@router.post("/", response_model=AllocationOut, status_code=status.HTTP_201_CREATED)
def create_allocation(budget_id: int, allocation: AllocationCreate, db: Session = Depends(get_db),
                      current_user: UserOut = Depends(get_current_user)):
    return AllocationService.add_allocation(
        db=db, budget_id=budget_id, user_id=current_user.id, data=allocation)
# put
# delete
