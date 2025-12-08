import logging
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from services.user_service import UserService
from services.auth_service import AuthService
from schema.user import UserUpdate, PasswordResetRequest

logger = logging.getLogger("app.user_profile_service")


class UserProfileService:

    # ----------------- Update User -----------------
    @staticmethod
    def update_user(db: Session, current_user, updates: UserUpdate):

        user = UserService.get_user_by_id(db, current_user.id)
        if not user:
            logger.warning("User not found: user_id=%s", current_user.id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Email update and duplicate email check
        if updates.email and updates.email != user.email:
            logger.info("User %s attempting to change email.", current_user.id)
            email_exists = UserService.get_user_by_email(db, updates.email)
            if email_exists:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already exists"
                )
            user.email = updates.email

        # First name / last name updates
        if updates.first_name:
            user.first_name = updates.first_name

        if updates.last_name:
            user.last_name = updates.last_name

        # Security answer update
        if updates.security_answer:
            user.security_answer = updates.security_answer

        user.updated_at = datetime.utcnow()

        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    # ----------------- Reset Password -----------------
    @staticmethod
    def reset_password(db: Session, request: PasswordResetRequest):

        user = UserService.get_user_by_email(db, request.email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Missing security answer check
        if not getattr(user, "security_answer", None):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security answer not configured for this account. Please contact support.",
            )

        # Validate security answer
        if user.security_answer.lower().strip() != request.security_answer.lower().strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect answer to security question"
            )

        # Hash & update the password using AuthService
        user.hashed_password = AuthService.hash_password(request.new_password)
        user.updated_at = datetime.utcnow()

        db.commit()
        return {"message": "Password reset successful"}
