"""Auth Router"""
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
    """
    Look up a user by email.

    Args:
        db (Session): SQLAlchemy session.
        email (str): User's email address.

    Returns:
        User | None: User object if found, otherwise None.
    """
    return db.query(User).filter(User.email == email).first()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a hashed password.

    Args:
        plain_password (str): The raw password input.
        hashed_password (str): The stored hashed password.

    Returns:
        bool: True if valid, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(db: Session, email: str, plain_password: str) -> Optional[User]:
    """
    Authenticate a user given an email and password.

    Args:
        db (Session): SQLAlchemy session.
        email (str): User's email.
        plain_password (str): User's plaintext password.

    Returns:
        User | None: User if credentials match, otherwise None.
    """
    user = get_user_by_email(db, email)
    if not user or not verify_password(plain_password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generate a JWT access token.

    Args:
        data (dict): Payload data to encode.
        expires_delta (timedelta, optional): Expiration time.

    Returns:
        str: Encoded JWT token.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Decode JWT and fetch the currently authenticated user from the DB.

    Args:
        token (str): JWT token from Authorization header.
        db (Session): SQLAlchemy session.

    Returns:
        User: Authenticated user.

    Raises:
        HTTPException: If token is invalid or user not found.
    """
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
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user_by_email(db, email)
    if not user or user.id != user_id:
        raise credentials_exception
    return user


# ----------- Routes -----------
@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login endpoint.

    Authenticates a user using email and password, then returns a JWT token.

    Request:
        {
            "username": "user1@example.com",
            "password": "password123"
        }

    Returns:
        Token: Access token and type.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    print()
    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user.

    Uses the token to fetch the user from the database.

    Returns:
        UserOut: Current logged-in user.
    """
    return current_user


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.

    Args:
        user (UserCreate): Incoming user data.
        db (Session): SQLAlchemy session.

    Raises:
        HTTPException: If email already exists.

    Returns:
        UserOut: The created user.
    """
    existing_user = get_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    new_user = User(
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        hashed_password=pwd_context.hash(user.password),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user
