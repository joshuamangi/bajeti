import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from core.security import get_current_user
from data.db.db import get_db
from data.db.models.models import User
from schema.user import UserUpdate, UserOut, PasswordResetRequest
from services.user_profile_service import UserProfileService

router = APIRouter(
    prefix="/api/users",
    tags=["users"]
)

logger = logging.getLogger("app.users")


@router.put("/me", response_model=UserOut, status_code=status.HTTP_200_OK)
async def update_user(
    updates: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return UserProfileService.update_user(db, current_user, updates)


@router.post("/password/reset")
async def reset_password(
    request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    return UserProfileService.reset_password(db, request)
