"""Requests File"""
from datetime import datetime
import os
import logging
from typing import Optional
from fastapi import APIRouter, Form, HTTPException, Request, Depends, status
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
API_BASE_URL = os.getenv("API_BASE_URL")

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


def get_current_user(request: Request):
    """Ensures there is a cookie and returns the user's token"""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/login"})

    token_data = verify_token(token)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_302_FOUND,
                            headers={"Location": "/login"})

    return token


def get_current_date():
    """Returns the current month"""
    current_date = datetime.now()
    return current_date


@router.get("/", response_class=HTMLResponse)
def welcome(request: Request):
    """Landing Page"""
    token = request.cookies.get("access_token")
    if token:
        token_data = verify_token(token)
        if token_data:
            return RedirectResponse(url="/dashboard", status_code=303)

    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    """Register Page"""
    return templates.TemplateResponse("register.html", {"request": request, "show_menu": False})


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
                "show_menu": False
            },
            status_code=400,
        )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/auth/",
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
    return templates.TemplateResponse("login.html",
                                      {"request": request, "show_menu": False})


@router.post("/login")
async def login_user(request: Request, username: str = Form(...), password: str = Form(...)):
    """Login user using the API auth/token route"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/auth/token",
            data={"username": username, "password": password}
        )

    if response.status_code != 200:
        logger.warning("Login failed for username=%s", username)
        return templates.TemplateResponse(
            "login.html",
            {"request": request,
             "error": "Invalid credentials",
             "username": username,
             "show_menu": False},
            status_code=401,
        )

    token_data = response.json()
    access_token = token_data["access_token"]
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=86400)

    return response


@router.get("/logout")
def logout():
    """Clear the auth cookie and redirect to login"""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
    return response


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, token: str = Depends(get_current_user)):
    """Main dashboard - requires JWT token in query param"""

    async with httpx.AsyncClient() as client:
        user_response = await client.get(
            f"{API_BASE_URL}/auth/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        if user_response.status_code != 200:
            logger.error("Failed to fetch user with token=%s", token)
            return RedirectResponse(url="/login", status_code=303)

        user = user_response.json()

        # Fetch categories + stats (current month)
        categories_response = await client.get(
            f"{API_BASE_URL}/categories/with-stats",
            headers={"Authorization": f"Bearer {token}"})
        if categories_response.status_code != 200:
            logger.error(
                "Failed to fetch categories with stats: %s", categories_response.text)
            categories_with_stats = []
        else:
            categories_with_stats = categories_response.json()

    current_date = get_current_date()
    current_month = current_date.strftime('%B')
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "categories_with_stats": categories_with_stats,
            "token": token,
            "current_month": current_month,
            "now": datetime.now().strftime("%Y-%m"),
            "show_menu": True
        }
    )

# ---------- Category management (from dashboard) ----------


@router.post("/dashboard/categories")
async def add_category(
    request: Request,
    name: str = Form(...),
    limit_amount: float = Form(...),
    token: str = Depends(get_current_user)
):
    """Add category via form on dashboard"""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/categories/",
            json={"name": name, "limit_amount": limit_amount},
            headers={"Authorization": f"Bearer {token}"}
        )

    if response.status_code == 201:
        return RedirectResponse(url=f"/dashboard", status_code=303)
    else:
        logger.error("Category creation failed: %s", response.text)
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "error": "Category creation failed",
                "token": token,
                "categories": [],
                "user": None,  # prevent Jinja crash,
                "show_menu": True

            },
            status_code=response.status_code,
        )


@router.post("/dashboard/categories/{category_id}/edit")
async def edit_category(
    request: Request,
    category_id: int,
    name: str = Form(...),
    limit_amount: float = Form(...),
    token: str = Depends(get_current_user)
):
    """Edit category via form on dashboard"""

    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{API_BASE_URL}/categories/{category_id}",
            json={"name": name, "limit_amount": limit_amount},
            headers={"Authorization": f"Bearer {token}"}
        )

    if response.status_code == 200:
        return RedirectResponse(url=f"/dashboard", status_code=303)
    else:
        logger.error("Category update failed: %s", response.text)
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "error": "Category update failed",
                "token": token,
                "categories": [],
                "user": None,  # prevent Jinja crash,
                "show_menu": True
            },
            status_code=response.status_code,
        )


@router.post("/dashboard/categories/{category_id}/delete")
async def delete_category(
    request: Request,
    category_id: int,
    token: str = Depends(get_current_user)
):
    """Delete category via form on dashboard"""

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{API_BASE_URL}/categories/{category_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

    if response.status_code == 204:
        return RedirectResponse(url=f"/dashboard", status_code=303)
    else:
        logger.error("Category deletion failed: %s", response.text)
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "error": "Category deletion failed",
                "token": token,
                "categories": [],
                "user": None,  # prevent Jinja crash,
                "show_menu": True
            },
            status_code=response.status_code,
        )

# ---------- Expense management (from table) ----------


@router.post("/dashboard/expenses")
async def add_expense(
        request: Request,
        category_id: int = Form(...),
        amount: float = Form(...),
        description: str = Form(""),
        month: Optional[str] = Form(None),
        token: str = Depends(get_current_user)
):
    """
    Add an expense in a category. If month omitted, backend can default to current month.
    """
    payload = {"category_id": category_id,
               "amount": amount, "description": description}
    if month:
        payload["month"] = month

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_BASE_URL}/expenses/",
                                     json=payload, headers={"Authorization": f"Bearer {token}"})

    if response.status_code == 201:
        logger.info("Expense Created: %s", response.json())
        return RedirectResponse(url=f"/dashboard", status_code=303)
    logger.error("Expense Creation Failed: %s", response.text)
    return templates.TemplateResponse("dashboard.html",
                                      {
                                          "request": request,
                                          "error": "Expense creation failed",
                                          "token": token,
                                          "user": None,
                                          "categories_with_stats": []
                                      }, status_code=response.status_code)


@router.post("/dashboard/expenses/{expense_id}/edit")
async def edit_expense(
        request: Request,
        expense_id: int,
        category_id: int = Form(...),
        amount: float = Form(...),
        description: str = Form(""),
        month: Optional[str] = Form(None),
        token: str = Depends(get_current_user)
):
    """Edits an Expense entry"""
    payload = {"category_id": category_id,
               "amount": amount, "description": description}
    if month:
        payload["month"] = month

    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{API_BASE_URL}/expenses/{expense_id}",
            json=payload, headers={"Authorization": f"Bearer {token}"})

    if response.status_code == 200:
        logger.info("Expense updated: %s", response.json())
        return RedirectResponse(url=f"/dashboard", status_code=303)
    logger.error("Expense update failed: %s", response.text)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "error": "Expense update failed",
            "token": token,
            "user": None,
            "categories_with_stats": []
        },
        status_code=response.status_code)


@router.post("/dashboard/expenses/{expense_id}/delete")
async def delete_expense(
    request: Request,
        expense_id: int,
        token: str = Depends(get_current_user)):
    """Deletes an expense entry"""

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{API_BASE_URL}/expenses/{expense_id}",
            headers={"Authorization": f"Bearer {token}"})

    if response.status_code == 204:
        logger.info("Expense deleted: id=%s", expense_id)
        return RedirectResponse(url=f"/dashboard", status_code=303)
    logger.error("Expense deletion failed: %s", response.text)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "error": "Expense deletion failed",
            "token": token,
            "user": None,
            "categories_with_stats": []
        },
        status_code=response.status_code)
