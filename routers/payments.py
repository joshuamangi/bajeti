from typing import Optional

from fastapi import APIRouter, Depends, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from core.security import get_capture_user, get_current_user
from data.db.db import get_db
from routers.analytics import to_json
from schema.payment import ApproveIn, CaptureIn, RecurringIn, SavingsIn
from schema.user import UserOut
from services.payment_service import PaymentService

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.post("/capture", status_code=status.HTTP_201_CREATED)
def capture(data: CaptureIn, db: Session = Depends(get_db), current_user: UserOut = Depends(get_capture_user)):
    """201 added to the inbox, 200 not spending (with the reason), 409 already captured.
    Accepts the login token or a phone token (the only endpoint that does)."""
    code, body = PaymentService.capture(db=db, user_id=current_user.id, data=data)
    return JSONResponse(status_code=code, content=jsonable_encoder(to_json(body)), media_type="application/json")


@router.get("/")
def pending(budget_id: Optional[int] = None, db: Session = Depends(get_db),
            current_user: UserOut = Depends(get_current_user)):
    return to_json(PaymentService.list_pending(db=db, user_id=current_user.id, budget_id=budget_id))


@router.get("/count")
def count(db: Session = Depends(get_db), current_user: UserOut = Depends(get_current_user)):
    return {"pending": PaymentService.count_pending(db=db, user_id=current_user.id)}


@router.post("/{payment_id}/approve", status_code=status.HTTP_201_CREATED)
def approve(payment_id: int, data: ApproveIn, db: Session = Depends(get_db),
            current_user: UserOut = Depends(get_current_user)):
    return to_json(PaymentService.approve(db=db, user_id=current_user.id, payment_id=payment_id, data=data))


@router.post("/{payment_id}/recurring", status_code=status.HTTP_201_CREATED)
def file_recurring(payment_id: int, data: RecurringIn, db: Session = Depends(get_db),
                   current_user: UserOut = Depends(get_current_user)):
    """This month's payment of a recurring item ({recurring_id}) or of a new one ({new: {...}})."""
    return to_json(PaymentService.file_recurring(db=db, user_id=current_user.id, payment_id=payment_id, data=data))


@router.post("/{payment_id}/savings", status_code=status.HTTP_201_CREATED)
def file_savings(payment_id: int, data: SavingsIn, db: Session = Depends(get_db),
                 current_user: UserOut = Depends(get_current_user)):
    """A bank message: a withdrawal from a savings category ({category_id}) or a deposit ({budget_id})."""
    return to_json(PaymentService.file_savings(db=db, user_id=current_user.id, payment_id=payment_id, data=data))


@router.post("/{payment_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
def dismiss(payment_id: int, db: Session = Depends(get_db), current_user: UserOut = Depends(get_current_user)):
    PaymentService.dismiss(db=db, user_id=current_user.id, payment_id=payment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{payment_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
def restore(payment_id: int, db: Session = Depends(get_db), current_user: UserOut = Depends(get_current_user)):
    PaymentService.restore(db=db, user_id=current_user.id, payment_id=payment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
