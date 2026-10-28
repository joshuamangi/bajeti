from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.security import get_current_user
from data.db.db import get_db
from schema.user import UserOut
from services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def to_json(value):
    """Money as strings with two decimals, percentages to one decimal."""
    if isinstance(value, Decimal):
        return format(value.quantize(Decimal("0.01")), "f")
    if isinstance(value, float):
        return round(value, 1)
    if isinstance(value, dict):
        return {k: to_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json(v) for v in value]
    return value


@router.get("/month")
def month(budget_id: int,
          month: Optional[str] = None,
          db: Session = Depends(get_db),
          current_user: UserOut = Depends(get_current_user)):
    return to_json(AnalyticsService.month(db=db, user_id=current_user.id, budget_id=budget_id, month=month))


@router.get("/trends")
def trends(budget_id: int,
           end: Optional[str] = None,
           months: int = Query(6),
           db: Session = Depends(get_db),
           current_user: UserOut = Depends(get_current_user)):
    return to_json(AnalyticsService.trends(db=db, user_id=current_user.id, budget_id=budget_id,
                                           end=end, months=months))


@router.get("/year")
def year(budget_id: int,
         year: Optional[int] = None,
         db: Session = Depends(get_db),
         current_user: UserOut = Depends(get_current_user)):
    return to_json(AnalyticsService.year(db=db, user_id=current_user.id, budget_id=budget_id, year=year))


@router.get("/category/{category_id}")
def category(category_id: int,
             month: Optional[str] = None,
             db: Session = Depends(get_db),
             current_user: UserOut = Depends(get_current_user)):
    return to_json(AnalyticsService.category(db=db, user_id=current_user.id,
                                             category_id=category_id, month=month))
