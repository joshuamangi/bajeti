from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class TransferBase(BaseModel):
    from_category_id: Optional[int] = None
    to_category_id: Optional[int] = None
    amount: float
    description: Optional[str] = None
    month: str


class TransferCreate(TransferBase):
    pass


class TransferOut(TransferBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
