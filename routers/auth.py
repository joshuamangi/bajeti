from datetime import datetime
from typing import Optional
from fastapi import APIRouter
from passlib.context import CryptContext

from schema.user import UserOut

router = APIRouter(prefix="/api/auth")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

mock_user = {
    "id": 1,
    "first_name": "Joshua",
    "last_name": "Masumbuo",
    "email": "joshuamangi@gmail.com",
    "hashed_password": pwd_context.hash("password123"),
    "created_at": datetime.utcnow()
}


def get_user(email: str) -> Optional[UserOut]:
    """Method used to return a user from email"""
    user = mock_user.get(email)
    if user:
        return UserOut(*user)
    return None


def verify_password(plain_password: str, hashed_password) -> bool:
    """Method of verifying password returns boolean"""
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(email: str, plain_password: str) -> Optional[UserOut]:
    """Method for authenticating user which returns Optional User"""
    user = get_user(email)
    if not user or not verify_password(
            plain_password=plain_password,
            hashed_password=user.hashed_password):
        return None
    return user


# Method for creating token
# Maethod for getting current user from authenticated token

# Only authenticated user can perform these

# Endpoint for login which returns token
# Endpoint for getting token which returns User
# Endpoint for creating User in DB returns Created
# Enpoint for editing user returns Edited User
# Endpoint for removing user returns No content or message
