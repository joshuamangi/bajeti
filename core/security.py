# core/security.py
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from data.db.db import get_db
from services.auth_service import AuthService
from services.user_service import UserService

logger = logging.getLogger("app.security")

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/token",
    scopes={"read": "Read access", "write": "Write access"}
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Resolve and return the current user from JWT token.
    Preserves the original behavior and error messages used by tests.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = AuthService.validate_token(token)
    if not payload:
        logger.error(
            "JWT decoding failed or token invalid for token=%s", token)
        raise credentials_exception

    email = payload.get("sub")
    user_id = payload.get("user_id")
    if email is None or user_id is None:
        logger.error("JWT payload invalid: %s", payload)
        raise credentials_exception

    user = UserService.get_user_by_email(db, email)
    if not user or user.id != user_id:
        logger.error(
            "User from token not found or ID mismatch: token_user_id=%s db_user_id=%s",
            user_id, getattr(user, "id", None)
        )
        raise credentials_exception

    logger.info("Current user resolved: id=%s email=%s", user.id, user.email)
    return user
