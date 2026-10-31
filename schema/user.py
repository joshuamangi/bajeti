from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

MIN_PASSWORD_LENGTH = 6  # kept simple on purpose: length only, no character rules


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
    password: str = Field(min_length=MIN_PASSWORD_LENGTH)
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
    has_security_answer: bool = False
    is_owner: bool = False


class UserUpdate(BaseModel):
    """Structure for updating user"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    security_answer: Optional[str] = None
    # Required when security_answer is set, so a borrowed session cannot set one and reset.
    current_password: Optional[str] = None


class PasswordResetRequest(BaseModel):
    """Schemafor resetting the password"""
    email: str
    security_answer: str
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH)


class PasswordChange(BaseModel):
    """Signed-in password change"""
    current_password: str
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH)


class ResetLinkUse(BaseModel):
    """The token from an owner-made reset link (sent in the body, not the URL)"""
    token: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH)


class ResetLinkOut(BaseModel):
    """Shown once to the owner; only its hash is stored"""
    token: str
    expires_at: datetime


class MemberOut(BaseModel):
    """A household member as the owner sees them in Admin"""
    id: int
    first_name: str
    last_name: str
    email: str
    is_owner: bool
    has_security_answer: bool
    created_at: datetime
    reset_link_expires_at: Optional[datetime] = None
