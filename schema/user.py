from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class Token(BaseModel):
    """Defines the Token structure"""
    access_token: str
    token_type: str


class UserBase(BaseModel):
    """Common fields across schemas"""
    first_name: str
    last_name: str
    email: str


class UserCreate(UserBase):
    """Request model for user creation (includes password)"""
    password: str
    security_answer: Optional[str] = None


class UserDB(UserBase):
    """Internal model with hashed password (not exposed to clients)"""
    id: int
    created_at: datetime
    updated_at: datetime
    hashed_password: str


class UserOut(UserBase):
    """Response model for user info"""
    id: int
    created_at: datetime
    updated_at: datetime
    security_answer: Optional[str] = None


class UserUpdate(BaseModel):
    """Structure for updating user"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    security_answer: Optional[str] = None


class PasswordResetRequest(BaseModel):
    """Schemafor resetting the password"""
    email: str
    security_answer: str
    new_password: str
