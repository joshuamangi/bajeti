# services/token_service.py
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict

import jwt

from app.config import settings

logger = logging.getLogger("app.token_service")

REMEMBER_ME_LIFETIME = timedelta(days=5)  # "Keep me signed in": the token and cookie last this long


class TokenService:
    @staticmethod
    def lifetime(remember: bool = False) -> timedelta:
        """How long one token lives: the setting, or 5 days for a remembered login."""
        if remember:
            return REMEMBER_ME_LIFETIME
        return timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    @staticmethod
    def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token with standard 'exp' claim."""
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
        to_encode = data.copy()
        to_encode.update({"exp": expire})
        token = jwt.encode(to_encode, settings.SECRET_KEY,
                           algorithm=settings.ALGORITHM)
        logger.debug("TokenService.create_access_token: user_id=%s exp=%s", data.get(
            "user_id"), expire)
        return token

    @staticmethod
    def decode_token(token: str) -> Optional[Dict]:
        """Decode a JWT token and return its payload, or None if invalid."""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY,
                                 algorithms=[settings.ALGORITHM])
            logger.debug(
                "TokenService.decode_token: payload keys=%s", list(payload.keys()))
            return payload
        except jwt.PyJWTError as e:
            logger.debug("TokenService.decode_token failed: %s", str(e))
            return None
