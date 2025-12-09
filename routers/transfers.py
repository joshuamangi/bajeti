# routers/transfers.py
import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from fastapi import HTTPException

from data.db.db import get_db
from data.db.models.models import Transfer
from schema.transfer import TransferCreate, TransferOut
from schema.user import UserOut
from core.security import get_current_user
from services.transfer_service import TransferService

logger = logging.getLogger("app.transfers")
router = APIRouter(prefix="/api/transfers", tags=["transfers"])


@router.get("/", response_model=list[TransferOut])
async def get_all_transfers(db: Session = Depends(get_db), current_user: UserOut = Depends(get_current_user)):
    return TransferService.get_all_transfers(db, current_user)


@router.get("/by-month", response_model=list[TransferOut])
async def get_transfers_by_month(month: str, db: Session = Depends(get_db), current_user: UserOut = Depends(get_current_user)):
    return TransferService.get_transfers_by_month(db, month, current_user)


@router.post("/", response_model=TransferOut, status_code=status.HTTP_201_CREATED)
async def create_transfer(payload: TransferCreate, db: Session = Depends(get_db), current_user: UserOut = Depends(get_current_user)):
    # minimal validation: amount > 0
    if payload.amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Transfer amount must be > 0")
    return TransferService.create_transfer(db, payload, current_user)


@router.delete("/{transfer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transfer(transfer_id: int, db: Session = Depends(get_db), current_user: UserOut = Depends(get_current_user)):
    TransferService.delete_transfer(db, transfer_id, current_user)
    return {}
