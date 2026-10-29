# Schemas for payment capture
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field


class CaptureIn(BaseModel):
    raw: str = Field(min_length=1, max_length=2000)
    source: Literal["paste", "sms", "email"] = "paste"


class ApproveIn(BaseModel):
    category_id: int
    # Leave out to use the parsed amount plus the fee.
    amount: Optional[Decimal] = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    remember: bool = False
