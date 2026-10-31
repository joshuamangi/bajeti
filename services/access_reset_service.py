import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from data.db.models.models import PasswordResetLink, User
from schema.user import ResetLinkUse
from services.auth_service import AuthService
from services.user_service import UserService

logger = logging.getLogger("app.access_reset_service")

LINK_LIFETIME = timedelta(hours=24)


class AccessResetService:
    """The owner resets a member's access: the member is logged out everywhere and gets a
    one-time link to set a new password. Only a hash of the link's token is stored."""

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    # ----------------- Members -----------------
    @staticmethod
    def list_members(db: Session):
        now = datetime.utcnow()
        users = db.query(User).order_by(User.is_owner.desc(), User.first_name, User.id).all()
        open_links = {
            link.user_id: link.expires_at
            for link in db.query(PasswordResetLink).filter(
                PasswordResetLink.used_at.is_(None), PasswordResetLink.expires_at > now)
        }
        return [{
            "id": u.id,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "email": u.email,
            "is_owner": bool(u.is_owner),
            "has_security_answer": u.has_security_answer,
            "created_at": u.created_at,
            "reset_link_expires_at": open_links.get(u.id),
        } for u in users]

    # ----------------- Reset access -----------------
    @staticmethod
    def reset_access(db: Session, owner, user_id: int):
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if user.id == owner.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Use Change password for your own account"
            )

        # One open link per member: a new one replaces any earlier link.
        db.query(PasswordResetLink).filter(
            PasswordResetLink.user_id == user.id, PasswordResetLink.used_at.is_(None)
        ).delete(synchronize_session=False)

        token = secrets.token_urlsafe(32)
        link = PasswordResetLink(
            user_id=user.id,
            created_by=owner.id,
            token_hash=AccessResetService.hash_token(token),
            expires_at=datetime.utcnow() + LINK_LIFETIME,
        )
        db.add(link)
        user.token_version = (user.token_version or 0) + 1  # log out every session
        db.commit()
        logger.info("Owner %s reset access for user %s", owner.id, user.id)
        return {"token": token, "expires_at": link.expires_at}

    # ----------------- Use the link -----------------
    @staticmethod
    def _open_link(db: Session, token: str):
        link = db.query(PasswordResetLink).filter(
            PasswordResetLink.token_hash == AccessResetService.hash_token(token)).first()
        if not link or link.used_at or link.expires_at <= datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This link has expired or was already used. Ask the owner for a new one."
            )
        return link

    @staticmethod
    def use_link(db: Session, request: ResetLinkUse):
        link = AccessResetService._open_link(db, request.token)
        user = UserService.get_user_by_id(db, link.user_id)

        user.hashed_password = AuthService.hash_password(request.new_password)
        user.token_version = (user.token_version or 0) + 1
        user.updated_at = datetime.utcnow()
        link.used_at = datetime.utcnow()
        db.commit()
        logger.info("User %s set a new password from a reset link", user.id)
        return AuthService.issue_token(user)
