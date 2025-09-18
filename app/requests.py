"""Requests File"""
import os
import logging
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import httpx
from jose import JWTError, jwt
from dotenv import load_dotenv

# Logging setup
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Load environment variables from .env file
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

# Setup templates
templates = Jinja2Templates(directory="app/templates")

router = APIRouter()


def verify_token(token: str):
    """Verify JWT Token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.error("Token verification failed: %s", e)
        return None


@router.get("/", response_class=HTMLResponse)
def welcome(request: Request):
    """Landing Page"""
    token = request.cookies.get("access_token")
    if token:
        token_data = verify_token(token)
        if token_data:
            return RedirectResponse(url="/dashboard", status_code=303)

    return templates.TemplateResponse("welcome.html", {"request": request})


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    """Register Page"""
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register")
async def register_user(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...)
):
    """Register User via API"""
    if password != confirm_password:
        logger.warning("Password mismatch for email=%s", email)
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,   # ✅ fixed
                "error": "Passwords do not match",
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
            },
            status_code=400,
        )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/auth/",
            json={
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password": password,
            }
        )

        if response.status_code == 201:
            return RedirectResponse(url="/dashboard", status_code=303)
        else:
            logger.error("User registration failed: %s", response.text)
            return templates.TemplateResponse(
                "register.html",
                {
                    "request": request,
                    "error": "Registration failed. Try again.",
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                },
                status_code=response.status_code,
            )


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Login Page"""
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login_user(request: Request, username: str = Form(...), password: str = Form(...)):
    """Login user using the API auth/token route"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/auth/token",
            data={"username": username, "password": password}
        )

    if response.status_code != 200:
        logger.warning("Login failed for username=%s", username)
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid credentials", "username": username},
            status_code=401,
        )

    token_data = response.json()
    access_token = token_data["access_token"]

    return RedirectResponse(f"/dashboard?token={access_token}", status_code=303)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, token: str):
    """Main dashboard - requires JWT token in query param"""
    async with httpx.AsyncClient() as client:
        user_response = await client.get(
            "http://localhost:8000/api/auth/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        if user_response.status_code != 200:
            logger.error("Failed to fetch user with token=%s", token)
            return RedirectResponse(url="/login", status_code=303)

        user = user_response.json()

        # Fetch categories
        categories_response = await client.get(
            "http://localhost:8000/api/categories/",
            headers={"Authorization": f"Bearer {token}"}
        )
        categories = categories_response.json(
        ) if categories_response.status_code == 200 else []

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,              # ✅ always passed
            "categories": categories,
            "token": token
        }
    )


@router.post("/dashboard/categories")
async def add_category(
    request: Request,
    name: str = Form(...),
    limit_amount: float = Form(...),
    token: str = Form(...)
):
    """Add category via form on dashboard"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/categories/",
            json={"name": name, "limit_amount": limit_amount},
            headers={"Authorization": f"Bearer {token}"}
        )

    if response.status_code == 201:
        return RedirectResponse(url=f"/dashboard?token={token}", status_code=303)
    else:
        logger.error("Category creation failed: %s", response.text)
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "error": "Category creation failed",
                "token": token,
                "categories": [],
                "user": None,  # prevent Jinja crash
            },
            status_code=response.status_code,
        )
