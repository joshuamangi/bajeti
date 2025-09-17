"""Requests File"""
import os
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import httpx
from jose import JWTError, jwt
from dotenv import load_dotenv

from data.db.models.models import User
from routers.auth import get_current_user

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
    except JWTError:
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
        first_name: str = Form(...),
        last_name: str = Form(...),
        email: str = Form(...),
        password: str = Form(...),
        confirm_password: str = Form(...)):
    """Register User via API"""
    if password != confirm_password:
        return templates.TemplateResponse(
            "register.html",
            {
                "request": {},
                "error": "Passwords do not match",
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
            }, status_code=400,
        )
    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:8000/api/auth/",
                                     json={
                                         "first_name": first_name,
                                         "last_name": last_name,
                                         "email": email,
                                         "password": password
                                     })

        if response.status_code == 201:
            return RedirectResponse(url="/dashboard", status_code=303)
        else:
            return RedirectResponse(url="/register?error=Registration+failed", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Login Page"""
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login_user(
        response: RedirectResponse,
        email: str = Form(...),
        password: str = Form(...)):
    """Login User via API"""
    async with httpx.AsyncClient() as client:
        api_response = await client.post("http://localhost:8000/api/auth/token",
                                         data={
                                             "username": email,
                                             "password": password
                                         })
        if api_response.status_code == 200:
            token_data = api_response.json()
            response = RedirectResponse(url="/dashboard", status_code=303)
            response.set_cookie(
                key="access_token",
                value=token_data["access_token"],
                httponly=True,
                max_age=1800,  # 30 minutes
                expires=1800,
                path="/"
            )
            return response
        else:
            return templates.TemplateResponse(
                "login.html",
                {
                    "request": {},
                    "error": "Invalid credentials",
                    "email": email
                }, status_code=400,
            )


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    """Main dashboard"""
    current_user: User = Depends(get_current_user)
    return templates.TemplateResponse(
        "dashboard.html",
        # replace with real user later
        {"request": request, "user": current_user}
    )
