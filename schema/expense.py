# Schema for Expenses

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Optional
from pydantic import BaseModel, StringConstraints

MonthStr = Annotated[str, StringConstraints(
    pattern=r'^\d{4}-(0[1-9]|1[0-2])$')]


class ExpenseBase(BaseModel):
    """describes the base structure for expenses"""
    amount: Decimal
    month: MonthStr
    description: Optional[str] = None


class ExpenseCreate(ExpenseBase):
    """describes the structure for the creation of an expense"""
    category_id: int
    user_id: int


class ExpenseOut(ExpenseBase):
    """describe the structure of the Expense object returned"""
    id: int
    category_id: int
    user_id: int
    created_at: datetime

    class Config:
        """describes the class that allows sqlalchemy objects"""
        orm_mode = True
