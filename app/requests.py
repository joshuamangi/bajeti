"""Requests File"""
from datetime import datetime
import os
import logging
from typing import Optional
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

        # Fetch categories + stats (current month)
        categories_response = await client.get(
            "http://localhost:8000/api/categories/with-stats",
            headers={"Authorization": f"Bearer {token}"})
        if categories_response.status_code != 200:
            logger.error(
                "Failed to fetch categories with stats: %s", categories_response.text)
            categories_with_stats = []
        else:
            categories_with_stats = categories_response.json()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "categories_with_stats": categories_with_stats,
            "token": token,
            "now": datetime.now().strftime("%Y-%m")
        }
    )

    # Fetch categories
    #     categories_response = await client.get(
    #         "http://localhost:8000/api/categories/",
    #         headers={"Authorization": f"Bearer {token}"}
    #     )
    #     categories = categories_response.json(
    #     ) if categories_response.status_code == 200 else ["No Categories, please add a category"]

    # return templates.TemplateResponse(
    #     "dashboard.html",
    #     {
    #         "request": request,
    #         "user": user,              # ✅ always passed
    #         "categories": categories,
    #         "token": token
    #     }
    # )

# ---------- Category management (from dashboard) ----------


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


@router.post("/dashboard/categories/{category_id}/edit")
async def edit_category(
    request: Request,
    category_id: int,
    name: str = Form(...),
    limit_amount: float = Form(...),
    token: str = Form(...)
):
    """Edit category via form on dashboard"""
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"http://localhost:8000/api/categories/{category_id}",
            json={"name": name, "limit_amount": limit_amount},
            headers={"Authorization": f"Bearer {token}"}
        )

    if response.status_code == 200:
        return RedirectResponse(url=f"/dashboard?token={token}", status_code=303)
    else:
        logger.error("Category update failed: %s", response.text)
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "error": "Category update failed",
                "token": token,
                "categories": [],
                "user": None,  # prevent Jinja crash
            },
            status_code=response.status_code,
        )


@router.post("/dashboard/categories/{category_id}/delete")
async def delete_category(
    request: Request,
    category_id: int,
    token: str = Form(...)
):
    """Delete category via form on dashboard"""
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"http://localhost:8000/api/categories/{category_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

    if response.status_code == 204:
        return RedirectResponse(url=f"/dashboard?token={token}", status_code=303)
    else:
        logger.error("Category deletion failed: %s", response.text)
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "error": "Category deletion failed",
                "token": token,
                "categories": [],
                "user": None,  # prevent Jinja crash
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
        token: str = Form(...)):
    """
    Add an expense in a category. If month omitted, backend can default to current month.
    """
    payload = {"category_id": category_id,
               "amount": amount, "description": description}
    if month:
        payload["month"] = month

    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:8000/api/expenses/",
                                     json=payload, headers={"Authorization": f"Bearer {token}"})

    if response.status_code == 201:
        logger.info("Expense Created: %s", response.json())
        return RedirectResponse(url=f"/dashboard?token={token}", status_code=303)
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
        token: str = Form(...)):
    """Edits an Expense entry"""
    payload = {"category_id": category_id,
               "amount": amount, "description": description}
    if month:
        payload["month"] = month

    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"http://localhost:8000/api/expenses/{expense_id}",
            json=payload, headers={"Authorization": f"Bearer {token}"})

    if response.status_code == 200:
        logger.info("Expense updated: %s", response.json())
        return RedirectResponse(url=f"/dashboard?token={token}", status_code=303)
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
        request: Request, expense_id: int, token: str = Form(...)):
    """Deletes an expense entry"""
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"http://localhost:8000/api/expenses/{expense_id}",
            headers={"Authorization": f"Bearer {token}"})

    if response.status_code == 204:
        logger.info("Expense deleted: id=%s", expense_id)
        return RedirectResponse(url=f"/dashboard?token={token}", status_code=303)
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
