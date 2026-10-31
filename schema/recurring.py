# Schemas for monthly recurring expenses
from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_serializer


class RecurringBase(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    category_id: int
    next_due: date
    mode: Literal["ask_first", "auto"] = "ask_first"
    # Usual M-Pesa fee, recorded in "M-Pesa fees" with each payment; leave out when there is none.
    usual_fee: Optional[Decimal] = Field(default=None, ge=0, max_digits=14, decimal_places=2)


class RecurringCreate(RecurringBase):
    pass


class RecurringUpdate(RecurringBase):
    pass


class DueDate(BaseModel):
    due_date: date


class RecurringOut(RecurringBase):
    id: int
    category_name: str
    anchor_day: int
    paused: bool

    @field_serializer("amount")
    def _two_decimals(self, value: Decimal):
        return format(value.quantize(Decimal("0.01")), "f")

    @field_serializer("usual_fee")
    def _fee_two_decimals(self, value: Optional[Decimal]):
        return None if value is None else format(value.quantize(Decimal("0.01")), "f")


class DueItem(RecurringOut):
    """An ask-first item with its oldest due date; overdue counts the due dates up to today."""
    due_date: date
    days: int
    overdue: int


class RunOut(BaseModel):
    recurring_id: int
    name: str
    due_date: date
    action: str
    amount: Optional[Decimal] = None

    @field_serializer("amount")
    def _two_decimals(self, value: Optional[Decimal]):
        return None if value is None else format(value.quantize(Decimal("0.01")), "f")
