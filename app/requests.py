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
from app.config import settings, ENVIRONMENT

# Logging setup
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
API_BASE_URL = settings.API_BASE_URL

# Setup templates
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["ENVIRONMENT"] = ENVIRONMENT

router = APIRouter()

# ---------- Helper Functions ----------


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
        raise HTTPException(status_code=status.HTTP_302_FOUND,
                            headers={"Location": "/login"})
    token_data = verify_token(token)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_302_FOUND,
                            headers={"Location": "/login"})
    return token


def get_current_date():
    """Returns the current datetime"""
    return datetime.now()


async def get_user_from_cookie(request: Request):
    """Extract user data from JWT cookie and fetch details"""
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/auth/users/me",
                                    headers={"Authorization": f"Bearer {token}"})
        if response.status_code == 200:
            return response.json()
    return None


async def render_with_user(template_name: str, request: Request, context: dict = None):
    """Render templates with global user context."""
    user = await get_user_from_cookie(request)
    if context is None:
        context = {}
    context.update({"request": request, "user": user})
    return templates.TemplateResponse(template_name, context)

# ---------------------------------- Routes ---------------------------------


@router.get("/", response_class=HTMLResponse)
async def welcome(request: Request):
    token = request.cookies.get("access_token")
    if token and verify_token(token):
        return RedirectResponse(url="/dashboard", status_code=303)
    return await render_with_user("login.html", request)


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return await render_with_user("register.html", request)


@router.post("/register")
async def register_user(request: Request,
                        first_name: str = Form(...),
                        last_name: str = Form(...),
                        email: str = Form(...),
                        password: str = Form(...),
                        confirm_password: str = Form(...),
                        security_answer: str = Form(...)):

    if password != confirm_password:
        return await render_with_user("register.html", request, {
            "error": "Passwords do not match",
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "security_answer": security_answer,
        })

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_BASE_URL}/auth/",
                                     json={
                                         "first_name": first_name,
                                         "last_name": last_name,
                                         "email": email,
                                         "password": password,
                                         "security_answer": security_answer
                                     })

    if response.status_code == 201:
        return RedirectResponse(url="/dashboard", status_code=303)
    return await render_with_user("register.html", request, {
        "error": "Registration failed. Try again.",
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "security_answer": security_answer,
    })


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return await render_with_user("login.html", request)


@router.post("/login")
async def login_user(request: Request,
                     username: str = Form(...),
                     password: str = Form(...)):

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_BASE_URL}/auth/token",
                                     data={"username": username, "password": password})

    if response.status_code != 200:
        return await render_with_user("login.html", request, {
            "error": "Invalid credentials",
            "username": username,
        })

    token_data = response.json()
    access_token = token_data["access_token"]

    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="access_token", value=access_token,
                        httponly=True, max_age=86400)
    response.set_cookie(key="show_menu", value="1",
                        httponly=False, max_age=86400)
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
    response.delete_cookie("show_menu")
    return response


@router.get("/forgot_password", response_class=HTMLResponse)
async def forgot_password(request: Request):
    return await render_with_user("forgot_password.html", request)


@router.post("/forgot_password")
async def reset_password(request: Request,
                         email: str = Form(...),
                         security_answer: str = Form(...),
                         new_password: str = Form(...)):

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{API_BASE_URL}/users/password/reset",
                                         json={"email": email, "security_answer": security_answer, "new_password": new_password})
    except httpx.RequestError:
        return await render_with_user("forgot_password.html", request, {
            "error": "Unable to reach server. Please try again later."
        })

    if response.status_code == 404:
        return await render_with_user("forgot_password.html", request, {"error": "User not found."})
    if response.status_code == 400:
        return await render_with_user("forgot_password.html", request, {"error": response.json().get("detail", "Invalid request.")})
    if response.status_code >= 500:
        return await render_with_user("forgot_password.html", request, {"error": "Server error. Try again later."})
    if response.status_code == 200:
        return RedirectResponse(url="/login", status_code=303)

    return await render_with_user("forgot_password.html", request, {
        "error": f"Unexpected response: {response.status_code}"
    })


@router.get("/profile", response_class=HTMLResponse)
async def profile(request: Request):
    """Describes the profile management"""
    return await render_with_user("profile.html", request)


@router.post("/profile/update")
async def profile_update(request: Request,
                         first_name: str = Form(...),
                         last_name: str = Form(...),
                         email: str = Form(...),
                         security_answer: str = Form(...)
                         ):

    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{API_BASE_URL}/users/me",
            json={
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "security_answer": security_answer
            },
            headers={
                "Authorization": f"Bearer {request.cookies.get('access_token')}"}
        )

    if response.status_code in (200, 201):
        # ✅ Handle success (200 OK from backend)
        return RedirectResponse(url="/dashboard", status_code=303)
    else:
        try:
            error_detail = response.json().get("detail", "Update failed. Try again.")
        except Exception:
            error_detail = "Unexpected error. Please try again."

        return await render_with_user("register.html", request, {
            "error": error_detail,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "security_answer": security_answer,
        })


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, token: str = Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        user_response = await client.get(f"{API_BASE_URL}/auth/users/me",
                                         headers={"Authorization": f"Bearer {token}"})
        if user_response.status_code != 200:
            return RedirectResponse(url="/login", status_code=303)

        user = user_response.json()
        categories_response = await client.get(
            f"{API_BASE_URL}/categories/with-stats",
            headers={"Authorization": f"Bearer {token}"})
        categories_with_stats = categories_response.json(
        ) if categories_response.status_code == 200 else []

    return await render_with_user("dashboard.html", request, {
        "categories_with_stats": categories_with_stats,
        "token": token,
        "current_month": datetime.now().strftime('%B'),
        "user": user,
        "now": datetime.now().strftime("%Y-%m"),
    })


# ---------- Category Management ----------

@router.post("/dashboard/categories")
async def add_category(request: Request,
                       name: str = Form(...),
                       limit_amount: float = Form(...),
                       token: str = Depends(get_current_user)):

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_BASE_URL}/categories/",
                                     json={"name": name,
                                           "limit_amount": limit_amount},
                                     headers={"Authorization": f"Bearer {token}"})

    if response.status_code == 201:
        return RedirectResponse(url="/dashboard", status_code=303)

    return await render_with_user("dashboard.html", request, {
        "error": "Category creation failed",
        "token": token,
        "categories_with_stats": [],
    })


@router.post("/dashboard/categories/{category_id}/edit")
async def edit_category(request: Request,
                        category_id: int,
                        name: str = Form(...),
                        limit_amount: float = Form(...),
                        token: str = Depends(get_current_user)):

    async with httpx.AsyncClient() as client:
        response = await client.put(f"{API_BASE_URL}/categories/{category_id}",
                                    json={"name": name,
                                          "limit_amount": limit_amount},
                                    headers={"Authorization": f"Bearer {token}"})

    if response.status_code == 200:
        return RedirectResponse(url="/dashboard", status_code=303)

    return await render_with_user("dashboard.html", request, {
        "error": "Category update failed",
        "token": token,
        "categories_with_stats": [],
    })


@router.post("/dashboard/categories/{category_id}/delete")
async def delete_category(request: Request,
                          category_id: int,
                          token: str = Depends(get_current_user)):

    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{API_BASE_URL}/categories/{category_id}",
                                       headers={"Authorization": f"Bearer {token}"})

    if response.status_code == 204:
        return RedirectResponse(url="/dashboard", status_code=303)

    return await render_with_user("dashboard.html", request, {
        "error": "Category deletion failed",
        "token": token,
        "categories_with_stats": [],
    })


# ---------- Expense Management ----------

@router.post("/dashboard/expenses")
async def add_expense(request: Request,
                      category_id: int = Form(...),
                      amount: float = Form(...),
                      description: str = Form(""),
                      month: Optional[str] = Form(None),
                      token: str = Depends(get_current_user)):

    payload = {"category_id": category_id,
               "amount": amount, "description": description}
    if month:
        payload["month"] = month

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_BASE_URL}/expenses/", json=payload,
                                     headers={"Authorization": f"Bearer {token}"})

    if response.status_code == 201:
        return RedirectResponse(url="/dashboard", status_code=303)

    return await render_with_user("dashboard.html", request, {
        "error": "Expense creation failed",
        "token": token,
        "categories_with_stats": [],
    })


@router.post("/dashboard/expenses/{expense_id}/edit")
async def edit_expense(request: Request,
                       expense_id: int,
                       category_id: int = Form(...),
                       amount: float = Form(...),
                       description: str = Form(""),
                       month: Optional[str] = Form(None),
                       token: str = Depends(get_current_user)):

    payload = {"category_id": category_id,
               "amount": amount, "description": description}
    if month:
        payload["month"] = month

    async with httpx.AsyncClient() as client:
        response = await client.put(f"{API_BASE_URL}/expenses/{expense_id}",
                                    json=payload, headers={"Authorization": f"Bearer {token}"})

    if response.status_code == 200:
        return RedirectResponse(url="/dashboard", status_code=303)

    return await render_with_user("dashboard.html", request, {
        "error": "Expense update failed",
        "token": token,
        "categories_with_stats": [],
    })


@router.post("/dashboard/expenses/{expense_id}/delete")
async def delete_expense(request: Request,
                         expense_id: int,
                         token: str = Depends(get_current_user)):

    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{API_BASE_URL}/expenses/{expense_id}",
                                       headers={"Authorization": f"Bearer {token}"})

    if response.status_code == 204:
        return RedirectResponse(url="/dashboard", status_code=303)

    return await render_with_user("dashboard.html", request, {
        "error": "Expense deletion failed",
        "token": token,
        "categories_with_stats": [],
    })


@router.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request):
    """Renders the reports page"""
    return await render_with_user("reports.html", request)


@router.get("/analytics", response_class=HTMLResponse)
async def reports_page(request: Request):
    """Renders the reports page"""
    return await render_with_user("analytics.html", request)


@router.get("/settings", response_class=HTMLResponse)
async def reports_page(request: Request):
    """Renders the reports page"""
    return await render_with_user("settings.html", request)
