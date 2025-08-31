from datetime import datetime
from fastapi import APIRouter, HTTPException, Response, status

from schema.expense import ExpenseCreate, ExpenseOut

router = APIRouter(prefix="/api/expenses")

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


@router.get("/")
async def get_all_expenses() -> list[ExpenseOut]:
    """Returns all the expensses by Id"""
    return expense_mock_data


@router.post("/", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
async def create_expense(expense: ExpenseCreate):
    """Creates an expense and add it to mock data"""
    new_id = max([c["id"] for c in expense_mock_data], default=0) + 1
    new_expense = ExpenseOut(
        id=new_id,
        user_id=expense.user_id,
        category_id=expense.category_id,
        amount=expense.amount,
        description=expense.description,
        month=expense.month,
        created_at=datetime.utcnow()
    )
    expense_mock_data.append(new_expense.model_dump())
    return expense_mock_data


@router.put("/{expense_id}", response_model=ExpenseOut)
def update_expense(expense_id: int, expense: ExpenseCreate) -> ExpenseOut:
    """Updates the contents of the expense to be updated"""
    for index, existing_expense in enumerate(expense_mock_data):
        if existing_expense["id"] == expense_id:
            updated_expense = ExpenseOut(
                id=expense_id,
                user_id=expense.user_id,
                category_id=expense.category_id,
                amount=expense.amount,
                description=expense.description,
                month=expense.month,
                created_at=datetime.utcnow()
            )
            expense_mock_data[index] = updated_expense.model_dump()
            return updated_expense
    raise HTTPException(status_code=404, detail="Expense not found")


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_expense(expense_id: int):
    """Deletes an instance of an expense matching the passed id"""
    for index, existing_expense in enumerate(expense_mock_data):
        if existing_expense["id"] == expense_id:
            expense_mock_data.pop(index)
            return Response(status_code=status.HTTP_204_NO_CONTENT)
    raise HTTPException(status_code=204, detail="No Content")
