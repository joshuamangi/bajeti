
from fastapi import APIRouter, Depends, status

from core.security import get_current_user
from data.db.db import get_db
from schema.allocation import AllocationBase, AllocationOut
from sqlalchemy.orm import Session

from services.allocation_service import AllocationService

router = APIRouter(prefix="/api/allocations", tags=["allocations"])
# get
# post


@router.post("/{budget_id}", response_model=list[AllocationOut], status_code=status.HTTP_201_CREATED)
async def add_allocation(allocation: AllocationBase, budget_id: int, db: Session = Depends(get_db),
                         current_user=Depends(get_current_user)):
    allocation_exists = AllocationService.check_allocaation_exists(db=db,)
# put
# delete
