# Schema for representing Targets
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TargetBase(BaseModel):
    """The three horizons. Any of them may be unset (None); amounts cannot be negative."""
    short_term_amount: Optional[Decimal] = Field(default=None, ge=0)
    mid_term_amount: Optional[Decimal] = Field(default=None, ge=0)
    long_term_amount: Optional[Decimal] = Field(default=None, ge=0)


class TargetCreate(TargetBase):
    category_id: int


class TargetUpdate(TargetBase):
    pass


class TargetOut(TargetBase):
    id: int
    budget_id: int
    category_id: int
    category_name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
