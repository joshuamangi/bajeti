"""Expenses router"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import and_

from data.db.db import get_db
from data.db.models.models import Expense
from routers.auth import get_current_user
from schema.expense import ExpenseCreate, ExpenseOut
from schema.user import UserOut

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
    """Returns all the expenses"""
    expenses = db.query(Expense).filter(
        Expense.user_id == current_user.id).all()
    if not expenses:
        raise HTTPException(
            status_code=404, detail="No expenses found for this user")
    return expenses


@router.get("/month", response_model=list[ExpenseOut])
async def get_current_month_expense(
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Gets the expenses from the current month"""
    current_year_month = datetime.utcnow().strftime("%Y-%m")
    expenses = db.query(Expense).filter(
        and_(
            Expense.month == current_year_month,
            Expense.user_id == current_user.id
        )
    ).all()

    if not expenses:
        raise HTTPException(
            status_code=404, detail=f"No expenses found for {current_year_month}"
        )
    return expenses


@router.get("/by-month", response_model=list[ExpenseOut])
async def get_expenses_by_month(
    month: str = Query(...,
                       regex=r"^\d{4}-(0[1-9]|1[0-2])$", description="Format: YYYY-MM"),
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all expenses for a given month (format: YYYY-MM)."""
    expenses = db.query(Expense).filter(
        and_(
            Expense.month == month,
            Expense.user_id == current_user.id
        )
    ).all()

    if not expenses:
        raise HTTPException(
            status_code=404, detail=f"No expenses found for {month}")
    return expenses


@router.get("/category/{category_id}", response_model=list[ExpenseOut])
async def get_expense_by_category(
    category_id: int = Path(..., description="Category ID"),
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all expenses for a specific category."""
    expenses = db.query(Expense).filter(
        and_(
            Expense.category_id == category_id,
            Expense.user_id == current_user.id
        )
    ).all()

    if not expenses:
        raise HTTPException(
            status_code=404, detail=f"No expenses found for category {category_id}"
        )
    return expenses


@router.get("/by-category-month", response_model=list[ExpenseOut])
async def get_expenses_by_category_and_month(
    category_id: int = Query(..., description="Category ID"),
    month: str = Query(...,
                       regex=r"^\d{4}-(0[1-9]|1[0-2])$", description="Format: YYYY-MM"),
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all expenses for a specific category in a specific month."""
    expenses = db.query(Expense).filter(
        and_(
            Expense.category_id == category_id,
            Expense.month == month,
            Expense.user_id == current_user.id
        )
    ).all()

    if not expenses:
        raise HTTPException(
            status_code=404,
            detail=f"No expenses found for category {category_id} in {month}"
        )
    return expenses


@router.post("/", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
async def create_expense(
    expense: ExpenseCreate,
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creates an expense"""
    now = datetime.utcnow()
    new_expense = Expense(
        user_id=current_user.id,
        category_id=expense.category_id,
        amount=expense.amount,
        description=expense.description,
        month=expense.month,
        created_at=now,
        updated_at=now
    )
    db.add(new_expense)
    db.commit()
    db.refresh(new_expense)
    return new_expense


@router.put("/{expense_id}", response_model=ExpenseOut)
def update_expense(
    expense_id: int,
    expense: ExpenseCreate,
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates the contents of the expense to be updated"""
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
    db_expense.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(db_expense)
    return db_expense


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_expense(
    expense_id: int,
    current_user: UserOut = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes an instance of an expense matching the passed id"""
    db_expense = db.query(Expense).filter(
        and_(
            Expense.id == expense_id,
            Expense.user_id == current_user.id
        )
    ).first()

    if not db_expense:
        raise HTTPException(
            status_code=404, detail="Expense not found or not yours"
        )

    db.delete(db_expense)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
