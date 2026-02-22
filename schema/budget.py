from datetime import datetime
from typing import Literal
from pydantic import BaseModel


class BudgetBase(BaseModel):
    name: str
    amount: float
    type: Literal["expense", "savings"] = "expense"


class BudgetOut(BudgetBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """defines a class that allows creation of SQL Alchemy objects"""
        orm_mode = True
