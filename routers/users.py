# routers/users.py
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from data.db.db import get_db
from data.db.models.models import User
from routers.auth import get_current_user
from schema.user import UserUpdate, UserOut

router = APIRouter(
    prefix="/api/users",
    tags=["users"]
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.put("/me", response_model=UserOut)
async def update_user(
    updates: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the logged-in user's profile.
    Only allows updating first_name, last_name, email, or password.
    """
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # check for duplicate email
    if updates.email and updates.email != user.email:
        email_exists = db.query(User).filter(
            User.email == updates.email).first()
        if email_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        user.email = updates.email

    if updates.first_name:
        user.first_name = updates.first_name
    if updates.last_name:
        user.last_name = updates.last_name
    if updates.password:
        user.hashed_password = pwd_context.hash(updates.password)

    # update timestamp (SQLAlchemy onupdate also covers this)
    user.updated_at = datetime.utcnow()

    db.add(user)
    db.commit()
    db.refresh(user)

    return user
