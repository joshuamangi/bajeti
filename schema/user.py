# schema for User

from datetime import datetime
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """defines the structure of the User that can be safely returned"""
    first_name: str
    email: EmailStr


class UserCreate(UserBase):
    """defines the structure for creating a user"""
    password: str


class UserOut(UserBase):
    """defines the structure for Useer data to be returned"""
    id: int
    created_at: datetime

    class Config:
        """allows for the creation of sql alchemy objects"""
        orm_mode = True
