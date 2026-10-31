import hashlib
import hmac
import secrets
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from data.db.models.models import ApiToken, User

PREFIX = "bjt_"
CAPTURE_SCOPE = "payments:capture"
MAX_PER_USER = 5


def _hash(plain: str) -> str:
    # The token is 32 random bytes, so a fast hash is enough; it is never stored in plain text.
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def is_phone_token(value: Optional[str]) -> bool:
    return bool(value) and value.startswith(PREFIX)


class ApiTokenService:

    @staticmethod
    def out(t: ApiToken, plain: Optional[str] = None) -> dict:
        body = {"id": t.id, "name": t.name, "prefix": t.prefix, "scope": t.scope,
                "created_at": t.created_at, "last_used_at": t.last_used_at}
        if plain:
            body["token"] = plain
        return body

    @staticmethod
    def list(db: Session, user_id: int) -> list:
        tokens = (db.query(ApiToken).filter(ApiToken.user_id == user_id)
                  .order_by(ApiToken.created_at.desc(), ApiToken.id.desc()).all())
        return [ApiTokenService.out(t) for t in tokens]

    @staticmethod
    def create(db: Session, user_id: int, name: str) -> dict:
        """Returns the token once. Only its hash is kept."""
        if db.query(ApiToken).filter(ApiToken.user_id == user_id).count() >= MAX_PER_USER:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"You can have up to {MAX_PER_USER} phone tokens. Revoke one first.")
        plain = PREFIX + secrets.token_urlsafe(32)
        token = ApiToken(user_id=user_id, name=name.strip(), token_hash=_hash(plain),
                         prefix=plain[:8], scope=CAPTURE_SCOPE, created_at=datetime.utcnow())
        db.add(token)
        db.commit()
        db.refresh(token)
        return ApiTokenService.out(token, plain)

    @staticmethod
    def revoke(db: Session, user_id: int, token_id: int):
        token = db.query(ApiToken).filter(ApiToken.id == token_id, ApiToken.user_id == user_id).first()
        if not token:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
        db.delete(token)
        db.commit()

    @staticmethod
    def resolve(db: Session, plain: str, scope: str) -> Optional[tuple]:
        """(token, user) for a valid token with this scope, else None. Records when it was used."""
        digest = _hash(plain)
        token = db.query(ApiToken).filter(ApiToken.token_hash == digest).first()
        if not token or not hmac.compare_digest(token.token_hash, digest) or token.scope != scope:
            return None
        user = db.query(User).filter(User.id == token.user_id).first()
        if not user:
            return None
        token.last_used_at = datetime.utcnow()
        db.commit()
        return token, user
