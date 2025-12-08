# api/auth.py (or data/api/auth.py as in your layout)
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from data.db.db import get_db
from data.db.models.models import User
from schema.user import UserCreate, UserOut, Token
from services.auth_service import AuthService
from core.security import get_current_user

logger = logging.getLogger("app.auth")
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user. Behavior and messages preserved.
    """
    return AuthService.register_user(db, user)


@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login to get access token. Returns same payload and error message as original.
    """
    return AuthService.login(db, form_data.username, form_data.password)


@router.get("/users/me", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Return current user"""
    logger.debug("Returning current user: id=%s email=%s",
                 current_user.id, current_user.email)
    return current_user
