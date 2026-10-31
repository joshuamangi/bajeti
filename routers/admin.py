import logging
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from core.security import get_current_owner
from data.db.db import get_db
from data.db.models.models import User
from schema.user import MemberOut, ResetLinkOut
from services.access_reset_service import AccessResetService

# Owner only: everyone else gets 404 from get_current_owner.
router = APIRouter(
    prefix="/api/admin",
    tags=["admin"]
)

logger = logging.getLogger("app.admin")


@router.get("/users", response_model=List[MemberOut])
async def list_members(owner: User = Depends(get_current_owner), db: Session = Depends(get_db)):
    return AccessResetService.list_members(db)


@router.post("/users/{user_id}/reset-access", response_model=ResetLinkOut,
             status_code=status.HTTP_201_CREATED)
async def reset_access(user_id: int, owner: User = Depends(get_current_owner),
                       db: Session = Depends(get_db)):
    return AccessResetService.reset_access(db, owner, user_id)
