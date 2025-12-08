# app/utils/tokens.py
from jose import jwt, JWTError
from fastapi import HTTPException, status
from fastapi import Request
from app.config import settings
import logging

logger = logging.getLogger(__name__)

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM


def verify_token(token: str):
    """Verify JWT Token. Returns payload or None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.debug("Token verification failed: %s", e)
        return None


def get_current_user(request: Request):
    """
    Ensures there is a cookie and returns the user's token string.
    This keeps original behaviour: raises a 302 redirect to /login if missing/invalid.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_302_FOUND,
                            headers={"Location": "/login"})
    token_data = verify_token(token)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_302_FOUND,
                            headers={"Location": "/login"})
    # original returned token string
    return token
