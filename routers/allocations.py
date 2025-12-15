
from fastapi import APIRouter, Depends, HTTPException, status

from core.security import get_current_user
from data.db.db import get_db
from schema.allocation import AllocationCreate, AllocationOut
from sqlalchemy.orm import Session

from schema.user import UserOut
from services.allocation_service import AllocationService

router = APIRouter(
    prefix="/api/budgets/{budget_id}/allocations", tags=["allocations"])
# get


@router.get("/{allocation_id}", response_model=AllocationOut, status_code=status.HTTP_200_OK)
def get_single_allocation(allocation_id: int,
                          budget_id: int,
                          db: Session = Depends(get_db),
                          current_user: UserOut = Depends(get_current_user)):
    allocation_exists = AllocationService.get_allocation_by_id(
        db=db, allocation_id=allocation_id, budget_id=budget_id)
    if not allocation_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Allocation not Found")

    return allocation_exists


@router.get("/", response_model=list[AllocationOut])
def get_all_allocations(budget_id: int, db: Session = Depends(get_db),
                        current_user: UserOut = Depends(get_current_user)):

    return AllocationService.fetch_all_allocations(db=db, budget_id=budget_id)


@router.put("/{allocation_id}", response_model=AllocationOut)
def edit_allocation(allocation_id: int,
                    budget_id: int,
                    allocation: AllocationCreate,
                    db: Session = Depends(get_db),
                    current_user: UserOut = Depends(get_current_user)):

    existing_allocation = AllocationService.get_allocation_by_id(
        db=db, budget_id=budget_id, allocation_id=allocation_id)
    if not existing_allocation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Allocation not Found")

    return AllocationService.update_allocation(
        db=db,
        allocation=allocation,
        existing_allocation=existing_allocation)


@router.post("/", response_model=AllocationOut, status_code=status.HTTP_201_CREATED)
def create_allocation(budget_id: int, allocation: AllocationCreate, db: Session = Depends(get_db),
                      current_user: UserOut = Depends(get_current_user)):
    return AllocationService.add_allocation(
        db=db, budget_id=budget_id, user_id=current_user.id, data=allocation)


@router.delete("/{allocation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_allocation(budget_id: int,
                      allocation_id: int,
                      db: Session = Depends(get_db),
                      current_user: UserOut = Depends(get_current_user)):

    existing_allocation = AllocationService.get_allocation_by_id(
        db=db, budget_id=budget_id, allocation_id=allocation_id)
    if not existing_allocation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Allocation not Found")

    AllocationService.remove_allocation(db=db, allocation=existing_allocation)
