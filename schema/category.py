# Schema for representing Category

from datetime import datetime

from pydantic import BaseModel
from typing import List, Literal, Optional

from schema.expense import ExpenseOut
from schema.transfer import TransferOut, TransferStats


class CategoryBase(BaseModel):
    """defines the structure of Category Base"""
    name: str
    type: Literal["expense", "savings"] = "expense"


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
    allocated_amount: float
    expenses: List[ExpenseOut]
    used: float
    transfers_in: List[TransferStats]
    transfers_out: List[TransferStats]
    total_transfers_in: float
    total_transfers_out: float


class CategoryProgress(BaseModel):
    """Cateogires progress for current month"""
    name: str
    used: float
    limit: float
    balance: float
