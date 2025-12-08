# services/token_service.py
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict

from jose import jwt, JWTError

from app.config import settings

logger = logging.getLogger("app.token_service")


class TokenService:
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
        except JWTError as e:
            logger.debug("TokenService.decode_token failed: %s", str(e))
            return None
