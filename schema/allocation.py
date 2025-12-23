# Define the base schema
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class AllocationCreate(BaseModel):
    category_id: int
    allocated_amount: float


class AllocationOut(AllocationCreate):
    id: int
    budget_id: int
    category_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """describes the class that allows sqlalchemy objects"""
        orm_mode = True
