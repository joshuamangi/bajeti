# Schema for representing Targets
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


MONEY = dict(default=None, ge=0, max_digits=14, decimal_places=2)


class TargetBase(BaseModel):
    """The three horizons. Any of them may be unset (None). Amounts are money: zero or more,
    at most two decimal places."""
    short_term_amount: Optional[Decimal] = Field(**MONEY)
    mid_term_amount: Optional[Decimal] = Field(**MONEY)
    long_term_amount: Optional[Decimal] = Field(**MONEY)

    @field_serializer("short_term_amount", "mid_term_amount", "long_term_amount")
    def _two_decimals(self, value: Optional[Decimal]):
        # SQLite hands back 1500.0000000000; show money as 1500.00.
        return None if value is None else format(value.quantize(Decimal("0.01")), "f")


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


class TermProgress(BaseModel):
    """Progress toward one horizon: the target, how far along (percent, may exceed 100) and what is left."""
    amount: Decimal
    percent: float
    remaining: Decimal

    @field_serializer("amount", "remaining")
    def _two_decimals(self, value: Decimal):
        return format(value.quantize(Decimal("0.01")), "f")


class TargetProgress(BaseModel):
    """A category's target with progress per horizon. A horizon without a target is None."""
    id: int
    short_term: Optional[TermProgress] = None
    mid_term: Optional[TermProgress] = None
    long_term: Optional[TermProgress] = None
