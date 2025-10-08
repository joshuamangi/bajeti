"""Auth Router"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from data.db.db import get_db
from data.db.models.models import User
from schema.user import UserCreate, UserOut, Token
from app.config import settings

# Set up logger
logger = logging.getLogger("app.auth")
logging.basicConfig(level=logging.INFO)

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"]
)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/token",
    scopes={"read": "Read access", "write": "Write access"}
)

# ----------- Helpers -----------


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Fetch user by email"""
    logger.debug("Looking up user with email=%s", email)
    return db.query(User).filter(User.email == email).first()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(db: Session, email: str, plain_password: str) -> Optional[User]:
    """Authenticate user credentials"""
    user = get_user_by_email(db, email)
    if not user:
        logger.warning(
            "Authentication failed: user with email=%s not found", email)
        return None
    if not verify_password(plain_password, user.hashed_password):
        logger.warning(
            "Authentication failed: wrong password for email=%s", email)
        return None
    logger.info("User authenticated successfully: id=%s email=%s",
                user.id, user.email)
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT Access Token"""
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, settings.SECRET_KEY,
                       algorithm=settings.ALGORITHM)
    logger.debug("Access token created for user_id=%s exp=%s",
                 data.get("user_id"), expire)
    return token


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY,
                             algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        if email is None or user_id is None:
            logger.error("JWT payload invalid: %s", payload)
            raise credentials_exception
        logger.debug("Decoded JWT for user_id=%s email=%s", user_id, email)
    except JWTError as e:
        logger.error("JWT decoding failed: %s", str(e))
        raise credentials_exception

    user = get_user_by_email(db, email)
    if not user or user.id != user_id:
        logger.error("User from token not found or ID mismatch: token_user_id=%s db_user_id=%s",
                     user_id, getattr(user, "id", None))
        raise credentials_exception

    logger.info("Current user resolved: id=%s email=%s", user.id, user.email)
    return user

# ----------- Routes -----------


@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login to get access token"""
    logger.info("Login attempt for email=%s", form_data.username)
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        logger.warning("Login failed for email=%s", form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires
    )
    logger.info("Login successful for email=%s", user.email)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Return current user"""
    logger.debug("Returning current user: id=%s email=%s",
                 current_user.id, current_user.email)
    return current_user


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    logger.info("Register attempt for email=%s", user.email)
    existing_user = get_user_by_email(db, user.email)
    if existing_user:
        logger.warning(
            "Registration failed: email=%s already exists", user.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    new_user = User(
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        hashed_password=pwd_context.hash(user.password),
        security_answer=user.security_answer,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info("New user registered: id=%s email=%s",
                new_user.id, new_user.email)
    return new_user
