# Schema for representing Category

from datetime import datetime

from pydantic import BaseModel
from typing import List, Optional

from schema.expense import ExpenseOut


class CategoryBase(BaseModel):
    """defines the structure of Category Base"""
    name: str
    limit_amount: float


class CategoryOut(CategoryBase):
    """defines the structure for return a category"""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """defines a class that allows creation of SQL Alchemy objects"""
        orm_mode = True


class CategoryStats(CategoryOut):
    """Category plus aggregated stats for dashboard"""
    expense_count: int
    balance: float
    expenses: List[ExpenseOut]
