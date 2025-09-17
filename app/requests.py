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
async def login_user(username: str = Form(...), password: str = Form(...)):
    """Login user using the API auth/token route"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/auth/token",  # adjust if different host/port
            data={"username": username, "password": password}
        )

    if response.status_code != 200:
        return RedirectResponse(url="/login?error=InvalidCredentials", status_code=303)

    token_data = response.json()
    access_token = token_data["access_token"]

    # ✅ return token in template or redirect with query param
    return RedirectResponse(f"/dashboard?token={access_token}", status_code=303)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, token: str):
    """Main dashboard - requires JWT token in query param"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/auth/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )

    if response.status_code != 200:
        return RedirectResponse(url="/login", status_code=303)

    user = response.json()
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": user, "token": token}
    )
