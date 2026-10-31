import logging
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from services.user_service import UserService
from services.auth_service import AuthService
from schema.user import UserUpdate, PasswordResetRequest, PasswordChange

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

        # Security answer update: it can reset the password, so it needs the password too.
        if updates.security_answer:
            UserProfileService.require_password(user, updates.current_password)
            user.security_answer = AuthService.hash_security_answer(
                updates.security_answer)

        user.updated_at = datetime.utcnow()

        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def require_password(user, password):
        if not password or not AuthService.verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )

    # ----------------- Change Password -----------------
    @staticmethod
    def change_password(db: Session, current_user, request: PasswordChange):
        """Signed-in change. Other sessions are logged out; the caller gets a new token."""
        user = UserService.get_user_by_id(db, current_user.id)
        UserProfileService.require_password(user, request.current_password)

        user.hashed_password = AuthService.hash_password(request.new_password)
        user.token_version = (user.token_version or 0) + 1  # log out other sessions
        user.updated_at = datetime.utcnow()

        db.commit()
        return AuthService.issue_token(user)

    # ----------------- Reset Password -----------------
    @staticmethod
    def reset_password(db: Session, request: PasswordResetRequest):

        user = UserService.get_user_by_email(db, request.email)

        # Unknown email, no answer set and a wrong answer all give the same reply, and the
        # same amount of work, so the response does not reveal which emails exist.
        stored = getattr(user, "security_answer", None) if user else None
        answer_ok = AuthService.verify_security_answer(
            request.security_answer, stored or AuthService.DUMMY_ANSWER_HASH)
        if not user or not stored or not answer_ok:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect email or security answer"
            )

        # Hash & update the password using AuthService
        user.hashed_password = AuthService.hash_password(request.new_password)
        user.token_version = (user.token_version or 0) + 1  # log out other sessions
        user.updated_at = datetime.utcnow()

        db.commit()
        return {"message": "Password reset successful"}
