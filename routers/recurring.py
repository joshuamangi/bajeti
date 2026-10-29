from typing import Optional

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from core.security import get_current_user
from data.db.db import get_db
from routers.analytics import to_json
from schema.recurring import DueDate, DueItem, RecurringCreate, RecurringOut, RecurringUpdate
from schema.user import UserOut
from services.recurring_service import RecurringService

router = APIRouter(prefix="/api/recurring", tags=["recurring"])


@router.get("/")
def list_recurring(budget_id: Optional[int] = None,
                   db: Session = Depends(get_db),
                   current_user: UserOut = Depends(get_current_user)):
    """Items (scoped to a budget when given), the monthly total and the last 10 runs."""
    return to_json(RecurringService.list(db=db, user_id=current_user.id, budget_id=budget_id))


@router.get("/due", response_model=list[DueItem])
def due(budget_id: Optional[int] = None,
        db: Session = Depends(get_db),
        current_user: UserOut = Depends(get_current_user)):
    """Ask-first items due within 5 days. Auto items that are due are recorded first."""
    return RecurringService.due(db=db, user_id=current_user.id, budget_id=budget_id)


@router.post("/", response_model=RecurringOut, status_code=status.HTTP_201_CREATED)
def create(data: RecurringCreate,
           db: Session = Depends(get_db),
           current_user: UserOut = Depends(get_current_user)):
    return RecurringService.create(db=db, user_id=current_user.id, data=data)


@router.put("/{recurring_id}", response_model=RecurringOut)
def update(recurring_id: int, data: RecurringUpdate,
           db: Session = Depends(get_db),
           current_user: UserOut = Depends(get_current_user)):
    return RecurringService.update(db=db, user_id=current_user.id, recurring_id=recurring_id, data=data)


@router.delete("/{recurring_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(recurring_id: int,
           db: Session = Depends(get_db),
           current_user: UserOut = Depends(get_current_user)):
    RecurringService.delete(db=db, user_id=current_user.id, recurring_id=recurring_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{recurring_id}/pause", response_model=RecurringOut)
def pause(recurring_id: int, db: Session = Depends(get_db), current_user: UserOut = Depends(get_current_user)):
    return RecurringService.set_paused(db=db, user_id=current_user.id, recurring_id=recurring_id, paused=True)


@router.post("/{recurring_id}/resume", response_model=RecurringOut)
def resume(recurring_id: int, db: Session = Depends(get_db), current_user: UserOut = Depends(get_current_user)):
    return RecurringService.set_paused(db=db, user_id=current_user.id, recurring_id=recurring_id, paused=False)


@router.post("/{recurring_id}/approve", status_code=status.HTTP_201_CREATED)
def approve(recurring_id: int, data: DueDate,
            db: Session = Depends(get_db),
            current_user: UserOut = Depends(get_current_user)):
    """Record the expense for that due date (in the due date's month). 409 if already recorded."""
    RecurringService.approve(db=db, user_id=current_user.id, recurring_id=recurring_id, due_date=data.due_date)
    return {"recorded": 1}


@router.post("/{recurring_id}/skip", status_code=status.HTTP_201_CREATED)
def skip(recurring_id: int, data: DueDate,
         db: Session = Depends(get_db),
         current_user: UserOut = Depends(get_current_user)):
    RecurringService.approve(db=db, user_id=current_user.id, recurring_id=recurring_id,
                             due_date=data.due_date, action="skipped")
    return {"recorded": 0}


@router.post("/{recurring_id}/approve-all", status_code=status.HTTP_201_CREATED)
def approve_all(recurring_id: int, db: Session = Depends(get_db), current_user: UserOut = Depends(get_current_user)):
    return {"recorded": RecurringService.approve_all(db=db, user_id=current_user.id, recurring_id=recurring_id)}


@router.delete("/{recurring_id}/runs/{due_date}", status_code=status.HTTP_204_NO_CONTENT)
def undo(recurring_id: int, due_date: str,
         db: Session = Depends(get_db),
         current_user: UserOut = Depends(get_current_user)):
    RecurringService.undo(db=db, user_id=current_user.id, recurring_id=recurring_id,
                          due_date=DueDate(due_date=due_date).due_date)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
