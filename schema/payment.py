# Schemas for payment capture
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class CaptureIn(BaseModel):
    raw: str = Field(min_length=1, max_length=2000)
    source: Literal["paste", "sms", "email"] = "paste"


class ApproveIn(BaseModel):
    category_id: int
    # The amount before the fee; leave out to use the parsed amount. The fee is its own expense.
    amount: Optional[Decimal] = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    remember: bool = False


class SavingsIn(BaseModel):
    """File a bank message: a withdrawal from a savings category, or a deposit into a savings budget."""
    category_id: Optional[int] = None
    budget_id: Optional[int] = None
    # Leave out to use the parsed amount.
    amount: Optional[Decimal] = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    remember: bool = False


class NewRecurringIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    category_id: int
    mode: Literal["ask_first", "auto"] = "ask_first"


class RecurringIn(BaseModel):
    """File a captured payment as a recurring payment: an existing item, or a new one."""
    recurring_id: Optional[int] = None
    new: Optional[NewRecurringIn] = None
    remember: bool = False

    @model_validator(mode="after")
    def _one_of(self):
        if (self.recurring_id is None) == (self.new is None):
            raise ValueError("Choose a recurring item or describe a new one")
        return self
