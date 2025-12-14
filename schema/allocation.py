# Define the base schema
from datetime import datetime
from pydantic import BaseModel


class AllocationBase(BaseModel):
    name: str
    allocated_amount: float


class AllocationOut(AllocationBase):
    id: int
    budget_id: int
    category_id: int
    created_at: datetime
    updated_at: datetime
