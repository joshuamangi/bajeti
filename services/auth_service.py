# services/auth_service.py
import logging
from datetime import timedelta
from typing import Optional

from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from services.user_service import UserService
from services.token_service import TokenService
from schema.user import UserCreate

from app.config import settings

logger = logging.getLogger("app.auth_service")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    # Checked when there is no real hash, so unknown emails cost the same time as known ones.
    DUMMY_ANSWER_HASH = pwd_context.hash("not-a-real-answer")

    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def normalize_answer(answer: str) -> str:
        return answer.strip().casefold()

    @staticmethod
    def hash_security_answer(answer: str) -> str:
        return pwd_context.hash(AuthService.normalize_answer(answer))

    @staticmethod
    def verify_security_answer(answer: str, hashed_answer: str) -> bool:
        try:
            return pwd_context.verify(AuthService.normalize_answer(answer), hashed_answer)
        except ValueError:
            # Not a hash yet (the deploy starts the app before the migration runs).
            return False

    # ---------- Authentication ----------
    @staticmethod
    def authenticate_user(db: Session, email: str, plain_password: str):
        """
        Return user if credentials are valid, otherwise None.
        (Preserves original logging and behavior.)
        """
        user = UserService.get_user_by_email(db, email)
        if not user:
            return None
        if not AuthService.verify_password(plain_password, user.hashed_password):
            return None
        return user

    # ---------- Registration ----------
    @staticmethod
    def register_user(db: Session, user: UserCreate):
        """
        Register a new user. Raises HTTPException(status=409) if email exists.
        Returns the created User model (SQLAlchemy).
        """
        existing = UserService.get_user_by_email(db, user.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already in use. Please Register using another email"
            )

        hashed = AuthService.hash_password(user.password)
        hashed_answer = (AuthService.hash_security_answer(user.security_answer)
                         if user.security_answer else None)
        new_user = UserService.create_user(
            db=db, user=user, hashed_password=hashed,
            hashed_security_answer=hashed_answer)
        return new_user

    # ---------- Login ----------
    @staticmethod
    def login(db: Session, email: str, password: str):
        """
        Login user. Raises HTTPException(401) if authentication fails.
        Returns dict with access_token and token_type to match original router expectations.
        """
        user = AuthService.authenticate_user(db, email, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = TokenService.create_access_token(
            data={"sub": user.email, "user_id": user.id},
            expires_delta=expires
        )
        return {"access_token": access_token, "token_type": "bearer"}

    # ---------- Token Validation ----------
    @staticmethod
    def validate_token(token: str):
        """
        Return payload dict if valid, otherwise None.
        The router / security layer will raise the HTTPException to keep message identical.
        """
        return TokenService.decode_token(token)
