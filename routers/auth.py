"""Auth Router"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext

from jose import JWTError, jwt
from schema.user import UserCreate, UserDB, UserOut, Token

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"])

SECRET_KEY = "793d5117a7cf19f5ce87e7798ade10ddcbf883836aab149d0972bac514b73b44"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 90

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/token",
    scopes={"read": "Read access", "write": "Write access"}
)

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


def get_user(email: str) -> Optional[UserDB]:
    """Returns user with specified email"""
    user = mock_user_data.get(email)
    if user:
        return UserDB(**user)
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


def get_current_user(
    token: str = Depends(oauth2_scheme)
) -> UserOut:  # Expose only safe fields
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
    except JWTError:
        raise credentials_exception

    user = get_user(email)
    if user is None or user.id != user_id:
        raise credentials_exception

    return UserOut(**user.model_dump())


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


@router.get("/users/me", response_model=UserOut)
async def read_users_me(current_user: UserDB = Depends(get_current_user)):
    """
        Endpoint for returning current user using the
        get_current_user depency and returns authenticated
        user
    """
    return current_user


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate):
    """Endpoint for creating User in DB returns Created User"""
    if user.email in mock_user_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    new_id = max([u["id"] for u in mock_user_data.values()], default=0) + 1

    new_user = UserDB(
        id=new_id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        hashed_password=pwd_context.hash(user.password),
        created_at=datetime.utcnow()
    )
    mock_user_data[user.email] = new_user.model_dump()
    return UserOut(**new_user.model_dump())

# Enpoint for editing user returns Edited User
# Endpoint for removing user returns No content or message
