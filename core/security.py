# core/security.py
import logging
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from core import rate_limit
from data.db.db import get_db
from services.api_token_service import CAPTURE_SCOPE, ApiTokenService, is_phone_token
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
        logger.error("JWT decoding failed or token invalid")
        raise credentials_exception

    email = payload.get("sub")
    user_id = payload.get("user_id")
    if email is None or user_id is None:
        logger.error("JWT payload invalid: %s", payload)
        raise credentials_exception

    user = UserService.get_user_by_email(db, email)
    # Tokens issued before token_version existed carry no "ver" and count as version 0.
    if user and payload.get("ver", 0) != user.token_version:
        logger.warning("Token version is out of date: user_id=%s", user_id)
        raise credentials_exception
    if not user or user.id != user_id:
        logger.error(
            "User from token not found or ID mismatch: token_user_id=%s db_user_id=%s",
            user_id, getattr(user, "id", None)
        )
        raise credentials_exception

    logger.info("Current user resolved: id=%s email=%s", user.id, user.email)
    return user


def get_capture_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """The login token, or a phone token (iPhone Shortcut). Used only by payment capture.

    Every other endpoint uses get_current_user, where a phone token fails JWT decoding, so a
    phone token can do nothing but add messages to its owner's inbox.
    """
    if not is_phone_token(token):
        return get_current_user(token=token, db=db)
    ip = rate_limit.client_ip(request)
    rate_limit.check_api_token(ip)
    found = ApiTokenService.resolve(db, token, CAPTURE_SCOPE)
    if not found:
        rate_limit.api_token_failed(ip)
        logger.warning("Unknown phone token used for capture")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This phone token is not valid. Create a new one on the Account page.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    phone_token, user = found
    rate_limit.check_capture(phone_token.id)
    return user
