from fastapi import APIRouter, Depends, HTTPException, Response, status

from core.security import get_current_user
from data.db.db import get_db
from schema.budget import BudgetBase, BudgetOut
from sqlalchemy.orm import Session

from schema.user import UserOut
from services.budget_service import BudgetService

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


@router.get("/", response_model=list[BudgetOut], status_code=status.HTTP_200_OK)
async def get_all_budgets(
        db: Session = Depends(get_db),
        current_user: UserOut = Depends(get_current_user)):
    return BudgetService.get_all_budgets(db=db, user_id=current_user.id)


@router.get("/current", response_model=BudgetOut)
async def get_current_budget(
        db: Session = Depends(get_db),
        current_user: UserOut = Depends(get_current_user)):

    budget = BudgetService.fetch_current_budget(db=db, user_id=current_user.id)

    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No budget found for user"
        )

    return budget


@router.get("/{budget_id}", response_model=BudgetOut)
async def get_single_budget(
    budget_id: int,
    db: Session = Depends(get_db),
        current_user: UserOut = Depends(get_current_user)):
    budget = BudgetService.get_budget_by_id(
        db=db, budget_id=budget_id, user_id=current_user.id)

    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Budget not Found")

    return budget


@router.post("/", response_model=BudgetOut, status_code=status.HTTP_201_CREATED)
async def create_budget(
        budget: BudgetBase,
        db: Session = Depends(get_db),
        current_user: UserOut = Depends(get_current_user)):
    existing_budget = BudgetService.check_budget_exists(
        db=db, user_id=current_user.id, budget=budget)
    if existing_budget:
        raise HTTPException(detail="Budget already exists",
                            status_code=status.HTTP_409_CONFLICT)

    return BudgetService.save_new_budget(db=db, user_id=current_user.id, budget=budget)


@router.put("/{budget_id}", response_model=BudgetOut)
async def edit_budget(budget_id: int,
                      updated_budget: BudgetBase,
                      db: Session = Depends(get_db),
                      current_user: UserOut = Depends(get_current_user)):
    existing_budget = BudgetService.get_budget_by_id(
        db=db, budget_id=budget_id, user_id=current_user.id)
    if not existing_budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Budget not Found")
    updated_budget = BudgetService.update_budget(
        db=db, updated_budget=updated_budget, existing_budget=existing_budget)
    return updated_budget


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(budget_id: int,
                        db: Session = Depends(get_db),
                        current_user: UserOut = Depends(get_current_user)):
    existing_budget = BudgetService.get_budget_by_id(
        db=db, budget_id=budget_id, user_id=current_user.id)
    if not existing_budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Budget not Found")

    BudgetService.remove_budget(db=db, budget=existing_budget)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
