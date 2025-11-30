import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from data.db.db import get_db
from data.db.models.models import User
from routers.auth import get_current_user
from schema.user import UserUpdate, UserOut, PasswordResetRequest

# --- Router setup ---
router = APIRouter(
    prefix="/api/users",
    tags=["users"]
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Secure logger setup ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


@router.put("/me", response_model=UserOut, status_code=status.HTTP_200_OK)
async def update_user(
    updates: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the logged-in user's profile.
    Only allows updating first_name, last_name, email, or password.
    """
    logger.info("User update request received for user_id=%s", current_user.id)

    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        logger.warning("User not found: user_id=%s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if updates.email and updates.email != user.email:
        logger.info("User %s attempting to change email.", current_user.id)
        email_exists = db.query(User).filter(
            User.email == updates.email).first()
        if email_exists:
            logger.warning(
                "Email update failed for user_id=%s: duplicate email=%s",
                current_user.id, updates.email
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists"
            )
        user.email = updates.email

    if updates.first_name:
        user.first_name = updates.first_name
    if updates.last_name:
        user.last_name = updates.last_name
    # if updates.password:
    #     logger.info(
    #         "User %s updated their password (hashed safely).", current_user.id)
    #     user.hashed_password = pwd_context.hash(updates.password)
    if updates.security_answer:
        logger.info("User %s updated their security answer.", current_user.id)
        user.security_answer = updates.security_answer

    user.updated_at = datetime.utcnow()

    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("User %s profile updated successfully.", current_user.id)
    return user


@router.post("/password/reset")
async def reset_password(
    request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Resets a user password using their email and security answer."""
    logger.info("Password reset requested for email=%s", request.email)

    user = db.query(User).filter(User.email == request.email).first()

    # Handle missing user
    if not user:
        logger.warning(
            "Password reset failed: user not found (%s)", request.email)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Handle missing security answer column or empty value
    if not getattr(user, "security_answer", None):
        logger.warning(
            "Password reset failed: no security answer configured for email=%s",
            request.email,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security answer not configured for this account. Please contact support.",
        )

    # Validate security answer
    if user.security_answer.lower().strip() != request.security_answer.lower().strip():
        logger.warning("Incorrect security answer for email=%s", request.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect answer to security question"
        )

    # Hash and update new password
    user.hashed_password = pwd_context.hash(request.new_password)
    user.updated_at = datetime.utcnow()
    db.commit()

    logger.info("Password successfully reset for email=%s", request.email)
    return {"message": "Password reset successful"}
