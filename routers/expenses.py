"""Expenses router"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.orm import Session

from core.security import get_current_user
from data.db.db import get_db
from schema.expense import ExpenseCreate, ExpenseOut
from schema.user import UserOut

from services.expense_service import ExpenseService

logger = logging.getLogger("app.expenses")
logging.basicConfig(level=logging.INFO)


router = APIRouter(
    prefix="/api/expenses",
    tags=["expenses"],
    dependencies=[Depends(get_current_user)]
)


@router.get("/", response_model=list[ExpenseOut])
async def get_all_expenses(
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return ExpenseService.get_all_expenses(db=db, current_user=current_user)


@router.get("/month", response_model=list[ExpenseOut])
async def get_current_month_expense(
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return ExpenseService.get_current_month_expense(db=db, current_user=current_user)


@router.get("/by-month", response_model=list[ExpenseOut])
async def get_expenses_by_month(
    month: str = Query(...,
                       regex=r"^\d{4}-(0[1-9]|1[0-2])$", description="Format: YYYY-MM"),
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return ExpenseService.get_expenses_by_month(
        db=db,
        month=month,
        current_user=current_user
    )


@router.get("/category/{category_id}", response_model=list[ExpenseOut])
async def get_expense_by_category(
    category_id: int = Path(..., description="Category ID"),
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return ExpenseService.get_expenses_by_category(
        db=db,
        category_id=category_id,
        current_user=current_user
    )


@router.get("/by-category-month", response_model=list[ExpenseOut])
async def get_expenses_by_category_and_month(
    category_id: int = Query(..., description="Category ID"),
    month: str = Query(...,
                       regex=r"^\d{4}-(0[1-9]|1[0-2])$", description="Format: YYYY-MM"),
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return ExpenseService.get_expenses_by_category_and_month(
        db=db,
        category_id=category_id,
        month=month,
        current_user=current_user
    )


@router.post("/", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
async def create_expense(
    expense: ExpenseCreate,
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return ExpenseService.create_expense(
        db=db,
        expense=expense,
        current_user=current_user
    )


@router.put("/{expense_id}", response_model=ExpenseOut)
def update_expense(
    expense_id: int,
    expense: ExpenseCreate,
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return ExpenseService.update_expense(
        db=db,
        expense_id=expense_id,
        expense=expense,
        current_user=current_user
    )


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_expense(
    expense_id: int,
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ExpenseService.delete_expense(
        db=db,
        expense_id=expense_id,
        current_user=current_user
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
