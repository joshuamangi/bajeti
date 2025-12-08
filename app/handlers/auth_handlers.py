# app/handlers/auth_handlers.py
import logging
from fastapi import Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from app.utils.templates import render_with_user
from app.utils.tokens import verify_token
from app.services.auth_service import login as auth_login, register as auth_register
from app.utils.redirects import redirect_with_toast

logger = logging.getLogger(__name__)
HTMLResponse = HTMLResponse  # expose for router reference


async def handle_authenticated_login(username: str, password: str, request: Request):
    """Handles the login for an authenticated user - same behaviour as before"""
    response = await auth_login(username, password)
    if response.status_code != status.HTTP_200_OK:
        return await render_with_user("login.html", request, {
            "error": "Invalid credentials",
            "username": username,
        })
    token_data = response.json()
    access_token = token_data["access_token"]

    rsp = RedirectResponse(
        url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    rsp.set_cookie(key="access_token", value=access_token,
                   httponly=True, max_age=86400)
    rsp.set_cookie(key="show_menu", value="1",
                   httponly=False, max_age=86400)
    return rsp


async def welcome(request: Request):
    token = request.cookies.get("access_token")
    if token and verify_token(token):
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return await render_with_user("login.html", request)


async def register_page(request: Request):
    return await render_with_user("register.html", request)


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

    response = await auth_register(first_name, last_name, email, password, security_answer)

    if response.status_code == status.HTTP_409_CONFLICT:
        return await render_with_user("register.html", request, {
            "error": f"Email already exists. Register using another email address",
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "security_answer": security_answer,
        })

    if response.status_code == status.HTTP_201_CREATED:
        # Get the token for the user
        return await handle_authenticated_login(username=email, password=password, request=request)


async def login_page(request: Request):
    return await render_with_user("login.html", request)


async def login_user(request: Request,
                     username: str = Form(...),
                     password: str = Form(...)):
    return await handle_authenticated_login(username=username, password=password, request=request)


def logout():
    response = RedirectResponse(
        url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    response.delete_cookie("show_menu")
    return response


async def forgot_password(request: Request):
    return await render_with_user("forgot_password.html", request)


async def reset_password(request: Request,
                         email: str = Form(...),
                         security_answer: str = Form(...),
                         new_password: str = Form(...)):
    try:
        # placeholder to keep signature (not used)
        response = await auth_register
    except Exception:
        response = None

    # we use user_service.reset_password in the real handler—handled elsewhere in router in old code.
    # This function will be overridden by user handler; left as placeholder to keep route mapping
    # The actual logic is in user handlers (see dashboard_handlers for reset_password usage)
    return await render_with_user("forgot_password.html", request, {
        "error": "Not implemented"
    })
