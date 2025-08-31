"""Auth Router"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext

from jose import JWTError, jwt
from schema.user import UserCreate, UserOut, Token

router = APIRouter(prefix="/api/auth")

SECRET_KEY = "793d5117a7cf19f5ce87e7798ade10ddcbf883836aab149d0972bac514b73b44"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

mock_user = {
    "joshuamangi@gmail.com": {
        "id": 1,
        "first_name": "Joshua",
        "last_name": "Masumbuo",
        "email": "joshuamangi@gmail.com",
        "hashed_password": pwd_context.hash("password123"),
        "created_at": datetime.utcnow()
    }
}


def get_user(email: str) -> Optional[UserOut]:
    """Method used to return a user from email"""
    user = mock_user.get(email)
    if user:
        return UserOut(**user)
    return None


def verify_password(plain_password: str, hashed_password) -> bool:
    """Method of verifying password returns boolean"""
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(email: str, plain_password: str) -> Optional[UserOut]:
    """Method for authenticating user which returns Optional User"""
    user = get_user(email)
    if not user or not verify_password(
            plain_password=plain_password,
            hashed_password=user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Method for creating token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> UserCreate:
    """Method for getting current user from authenticated token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        if email is None or user_id is None:
            raise credentials_exception
    except JWTError as could_not_validate:
        raise credentials_exception from could_not_validate

    user = get_user(email)
    if user is None or user.id != user_id:
        raise credentials_exception

    return user


@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
        Endpoint for login which returns token
        Request {"username: "user1@example.com", "password: "password123"}
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", response_model=UserCreate)
async def read_users_me(current_user: UserCreate = Depends(get_current_user)):
    """
        Endpoint for returning current user using the
        get_current_user depency and returns authenticated
        user
    """
    return current_user


# Endpoint for creating User in DB returns Created
# Enpoint for editing user returns Edited User
# Endpoint for removing user returns No content or message
