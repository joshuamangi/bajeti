from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from core.security import get_current_user
from data.db.db import get_db
from schema.target import TargetCreate, TargetOut, TargetUpdate
from schema.user import UserOut
from services.target_service import TargetService

router = APIRouter(
    prefix="/api/budgets/{budget_id}/targets", tags=["targets"]
)


@router.get("/", response_model=list[TargetOut], status_code=status.HTTP_200_OK)
def get_targets(
        budget_id: int,
        db: Session = Depends(get_db),
        current_user: UserOut = Depends(get_current_user)):
    return TargetService.get_targets_by_budget(
        db=db, user_id=current_user.id, budget_id=budget_id)


@router.post("/", response_model=TargetOut, status_code=status.HTTP_201_CREATED)
def create_target(
        budget_id: int,
        target: TargetCreate,
        response: Response,
        db: Session = Depends(get_db),
        current_user: UserOut = Depends(get_current_user)):
    """201 when created, 200 when it updated the existing (for example backfilled) target."""
    result, created = TargetService.create_target(
        db=db, user_id=current_user.id, budget_id=budget_id, data=target)
    if not created:
        response.status_code = status.HTTP_200_OK
    return result


@router.put("/{target_id}", response_model=TargetOut)
def update_target(
        budget_id: int,
        target_id: int,
        target: TargetUpdate,
        db: Session = Depends(get_db),
        current_user: UserOut = Depends(get_current_user)):
    return TargetService.update_target(
        db=db, user_id=current_user.id, budget_id=budget_id,
        target_id=target_id, data=target)


@router.delete("/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_target(
        budget_id: int,
        target_id: int,
        db: Session = Depends(get_db),
        current_user: UserOut = Depends(get_current_user)):
    TargetService.delete_target(
        db=db, user_id=current_user.id, budget_id=budget_id, target_id=target_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
