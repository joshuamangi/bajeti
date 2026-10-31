from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from core.security import get_current_user
from data.db.db import get_db
from schema.api_token import ApiTokenIn
from schema.user import UserOut
from services.api_token_service import ApiTokenService

# Managed with the login token only: a phone token cannot list, create or revoke tokens.
router = APIRouter(prefix="/api/tokens", tags=["tokens"])


@router.get("/")
def list_tokens(db: Session = Depends(get_db), current_user: UserOut = Depends(get_current_user)):
    return ApiTokenService.list(db=db, user_id=current_user.id)


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_token(data: ApiTokenIn, db: Session = Depends(get_db), current_user: UserOut = Depends(get_current_user)):
    """The token is in this reply only."""
    return ApiTokenService.create(db=db, user_id=current_user.id, name=data.name)


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_token(token_id: int, db: Session = Depends(get_db), current_user: UserOut = Depends(get_current_user)):
    ApiTokenService.revoke(db=db, user_id=current_user.id, token_id=token_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
