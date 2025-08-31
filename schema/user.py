# Models the user
from datetime import datetime
from pydantic import BaseModel


class Token(BaseModel):
    """Defines the Token structure"""
    access_token: str
    token_type: str


class UserBase(BaseModel):
    """Defines the Base structure for creating a User"""
    first_name: str
    last_name: str
    email: str
    password: str


class UserCreate(BaseModel):
    """Defines the structure for a User being Created and without hidden information"""
    id: int
    first_name: str
    last_name: str
    email: str
    created_at: datetime


class UserOut(UserCreate):
    """Defines the structure for the User created in the database"""
    hashed_password: str
