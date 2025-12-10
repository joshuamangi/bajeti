import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from data.db.models.models import Transfer
from schema.transfer import TransferCreate
from schema.user import UserOut
from fastapi import HTTPException, status


logger = logging.getLogger("app.transfers")


class TransferService:
    @staticmethod
    def get_all_transfers(db: Session, current_user: UserOut):
        transfers = db.query(Transfer).filter(
            Transfer.user_id == current_user.id
        ).all()

        if not transfers:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No transfers found for this user"
            )

        return transfers

    @staticmethod
    def get_transfers_by_month(db: Session, month: str, current_user: UserOut):
        transfers = db.query(Transfer).filter(
            and_(
                Transfer.month == month,
                Transfer.user_id == current_user.id
            )
        ).all()

        if not transfers:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No transfers found for {month}"
            )

        return transfers

    @staticmethod
    def create_transfer(db: Session, payload: TransferCreate, current_user: UserOut):
        now = datetime.utcnow()

        new_transfer = Transfer(
            user_id=current_user.id,
            from_category_id=payload.from_category_id,
            to_category_id=payload.to_category_id,
            amount=payload.amount,
            description=payload.description,
            month=payload.month,
            created_at=now,
            updated_at=now
        )

        db.add(new_transfer)
        db.commit()
        db.refresh(new_transfer)

        return new_transfer

    @staticmethod
    def delete_transfer(db: Session, transfer_id: int, current_user: UserOut):
        db_transfer = db.query(Transfer).filter(
            and_(
                Transfer.id == transfer_id,
                Transfer.user_id == current_user.id
            )
        ).first()

        if not db_transfer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transfer not found or not yours"
            )

        db.delete(db_transfer)
        db.commit()

        return {"message": "Transfer deleted successfully"}
