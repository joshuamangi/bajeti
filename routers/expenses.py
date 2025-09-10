"""Expenses router"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status

from routers.auth import get_current_user
from schema.expense import ExpenseCreate, ExpenseOut
from schema.user import UserOut

router = APIRouter(
    prefix="/api/expenses",
    tags=["expenses"],
    dependencies=[Depends(get_current_user)]
)

expense_mock_data: list[ExpenseOut] = [
    {
        "id": 1,
        "amount": 2000,
        "month": "2025-08",
        "description": "",
        "category_id": 1,
        "user_id": 1,
        "created_at": "2025-07-31T21:14:03.581Z"
    }, {
        "id": 2,
        "amount": 9000,
        "month": "2025-08",
        "description": "",
        "category_id": 3,
        "user_id": 1,
        "created_at": "2025-07-31T21:14:03.581Z"
    }
]


@router.get("/", response_model=list[ExpenseOut])
async def get_all_expenses(current_user: UserOut = Depends(get_current_user)):
    """Returns all the expenses"""
    expenses = [e for e in expense_mock_data if e["user_id"] == current_user.id]
    if not expenses:
        raise HTTPException(
            status_code=404, detail="No expenses found for this user")
    return expenses


@router.get("/month", response_model=list[ExpenseOut])
async def get_current_month_expense(current_user: UserOut = Depends(get_current_user)):
    """Gets the expenses from the current month"""
    current_year_month = datetime.utcnow().strftime("%Y-%m")
    filtered_expenses = [
        expense for expense in expense_mock_data
        if expense["month"] == current_year_month and expense["user_id"] == current_user.id
    ]
    if not filtered_expenses:
        raise HTTPException(
            status_code=404, detail=f"No expenses found for {current_year_month}")
    return filtered_expenses


@router.get("/by-month", response_model=list[ExpenseOut])
async def get_expenses_by_month(
    month: str = Query(...,
                       regex=r"^\d{4}-(0[1-9]|1[0-2])$", description="Format: YYYY-MM"),
    current_user: UserOut = Depends(get_current_user)
):
    """Get all expenses for a given month (format: YYYY-MM)."""
    filtered_expenses = [
        expense for expense in expense_mock_data
        if expense["month"] == month and expense["user_id"] == current_user.id
    ]
    if not filtered_expenses:
        raise HTTPException(
            status_code=404, detail=f"No expenses found for {month}")
    return filtered_expenses


@router.get("/category/{category_id}", response_model=list[ExpenseOut])
async def get_expense_by_category(
    category_id: int = Path(..., description="Category ID"),
    current_user: UserOut = Depends(get_current_user)
):
    """Get all expenses for a specific category."""
    filtered_expenses = [
        expense for expense in expense_mock_data
        if expense["category_id"] == category_id and expense["user_id"] == current_user.id
    ]
    if not filtered_expenses:
        raise HTTPException(
            status_code=404, detail=f"No expenses found for category {category_id}")
    return filtered_expenses


@router.get("/by-category-month", response_model=list[ExpenseOut])
async def get_expenses_by_category_and_month(
    category_id: int = Query(..., description="Category ID"),
    month: str = Query(...,
                       regex=r"^\d{4}-(0[1-9]|1[0-2])$", description="Format: YYYY-MM"),
    current_user: UserOut = Depends(get_current_user)
):
    """Get all expenses for a specific category in a specific month."""
    filtered_expenses = [
        expense for expense in expense_mock_data
        if expense["category_id"] == category_id
        and expense["month"] == month
        and expense["user_id"] == current_user.id
    ]
    if not filtered_expenses:
        raise HTTPException(
            status_code=404,
            detail=f"No expenses found for category {category_id} in {month}"
        )
    return filtered_expenses


@router.post("/", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
async def create_expense(
    expense: ExpenseCreate,
    current_user: UserOut = Depends(get_current_user)
):
    """Creates an expense and add it to mock data"""
    new_id = max([c["id"] for c in expense_mock_data], default=0) + 1
    new_expense = ExpenseOut(
        id=new_id,
        user_id=current_user.id,
        category_id=expense.category_id,
        amount=expense.amount,
        description=expense.description,
        month=expense.month,
        created_at=datetime.utcnow()
    )
    expense_mock_data.append(new_expense.model_dump())
    return new_expense


@router.put("/{expense_id}", response_model=ExpenseOut)
def update_expense(
        expense_id: int,
        expense: ExpenseCreate,
        current_user: UserOut = Depends(get_current_user)):
    """Updates the contents of the expense to be updated"""
    for index, existing_expense in enumerate(expense_mock_data):
        if existing_expense["id"] == expense_id and existing_expense["user_id"] == current_user.id:
            updated_expense = ExpenseOut(
                id=expense_id,
                user_id=current_user.id,
                category_id=expense.category_id,
                amount=expense.amount,
                description=expense.description,
                month=expense.month,
                created_at=datetime.utcnow()
            )
            expense_mock_data[index] = updated_expense.model_dump()
            return updated_expense
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail="Expense not found or not yours")


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_expense(
    expense_id: int,
    current_user: UserOut = Depends(get_current_user)
):
    """Deletes an instance of an expense matching the passed id"""
    for index, existing_expense in enumerate(expense_mock_data):
        if existing_expense["id"] == expense_id and existing_expense["user_id"] == current_user.id:
            expense_mock_data.pop(index)
            return Response(status_code=status.HTTP_204_NO_CONTENT)
    raise HTTPException(
        status_code=404, detail="Expense not found or not yours")
