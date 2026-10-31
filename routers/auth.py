# api/auth.py (or data/api/auth.py as in your layout)
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from data.db.db import get_db
from data.db.models.models import User
from schema.user import UserCreate, UserOut, Token, ResetLinkUse
from services.access_reset_service import AccessResetService
from services.auth_service import AuthService
from core import rate_limit
from core.registration import require_registration_open
from core.security import get_current_user

logger = logging.getLogger("app.auth")
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_registration_open)])
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user. Behavior and messages preserved.
    """
    return AuthService.register_user(db, user)


@router.post("/token", response_model=Token)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login to get access token. Returns same payload and error message as original.
    """
    ip = rate_limit.client_ip(request)
    rate_limit.check_login(ip, form_data.username)
    try:
        token = AuthService.login(db, form_data.username, form_data.password)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            rate_limit.login_failed(ip, form_data.username)
        raise
    rate_limit.login_succeeded(ip, form_data.username)
    return token


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_everywhere(current_user: User = Depends(get_current_user),
                            db: Session = Depends(get_db)):
    """Invalidate every token of this user, including the one used for this call."""
    AuthService.revoke_all_tokens(db, current_user)


@router.get("/users/me", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Return current user"""
    logger.debug("Returning current user: id=%s email=%s",
                 current_user.id, current_user.email)
    return current_user


# The link's token goes in the body, and the web page keeps it in the URL fragment, which the
# browser never sends, so it stays out of access logs.
# One address cannot try many tokens: failures count against a per-address limit.
RESET_LINK_KEY = "reset-link"


@router.post("/reset-link", response_model=Token)
async def use_reset_link(http_request: Request, request: ResetLinkUse, db: Session = Depends(get_db)):
    ip = rate_limit.client_ip(http_request)
    rate_limit.check_reset(ip, RESET_LINK_KEY)
    try:
        return AccessResetService.use_link(db, request)
    except HTTPException:
        rate_limit.reset_failed(ip, RESET_LINK_KEY)
        raise
