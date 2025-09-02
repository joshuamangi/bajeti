"""Handles Editing User and Deletion Operations"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from routers.auth import get_current_user
from schema.user import UserCreate, UserOut, UserUpdate

router = APIRouter(
    prefix="/api/users",
    tags=["users"]
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

mock_user_data = {
    "joshuamangi@gmail.com": {
        "id": 1,
        "first_name": "Joshua",
        "last_name": "Masumbuo",
        "email": "joshuamangi@gmail.com",
        "hashed_password": pwd_context.hash("password123"),
        "created_at": datetime.utcnow()
    }
}


@router.put("/me")
async def update_user(
    updates: UserUpdate,
    current_user: UserCreate = Depends(get_current_user)
):
    """
    Update the logged-in user's profile.
    Only allows updating first_name, last_name, email, or password.
    """
    stored_user = mock_user_data.get(current_user.email)
    if not stored_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Keep track of the key (email) since it might change
    current_email = current_user.email

    if updates.first_name:
        stored_user["first_name"] = updates.first_name
    if updates.last_name:
        stored_user["last_name"] = updates.last_name
    if updates.email:
        # check for duplicates
        if updates.email in mock_user_data:
            raise HTTPException(status_code=400, detail="Email already exists")
        # move user record under new email
        mock_user_data[updates.email] = mock_user_data.pop(current_email)
        current_email = updates.email
        stored_user["email"] = updates.email
    if updates.password:
        stored_user["hashed_password"] = pwd_context.hash(updates.password)

    stored_user["updated_at"] = datetime.utcnow()
    mock_user_data[current_email] = stored_user

    return UserOut(**stored_user)
