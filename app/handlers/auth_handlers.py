# app/handlers/auth_handlers.py
import logging
from fastapi import Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from core.rate_limit import client_ip
from core.registration import require_registration_open
from app.utils.templates import render_with_user
from app.utils.tokens import verify_token
from app.services.auth_service import (
    login as auth_login, logout_everywhere as auth_logout_everywhere, register as auth_register)
from app.utils.cookies import clear_active_budget_cookie, clear_auth_cookies, set_auth_cookies
from app.utils.redirects import redirect_with_toast
from app.services.user_service import (
    reset_password as svc_reset_password, use_reset_link as svc_use_reset_link)
from schema.user import MIN_PASSWORD_LENGTH

logger = logging.getLogger(__name__)
HTMLResponse = HTMLResponse  # expose for router reference


async def handle_authenticated_login(username: str, password: str, request: Request):
    """Handles the login for an authenticated user - same behaviour as before"""
    response = await auth_login(username, password, client_ip=client_ip(request))
    if response.status_code != status.HTTP_200_OK:
        too_many = response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        return await render_with_user("login.html", request, {
            "error": ("Too many attempts. Please wait a few minutes and try again."
                      if too_many else "Invalid credentials"),
            "username": username,
        })
    token_data = response.json()
    access_token = token_data["access_token"]

    rsp = RedirectResponse(
        url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    set_auth_cookies(rsp, access_token)
    clear_active_budget_cookie(rsp)
    return rsp


async def welcome(request: Request):
    token = request.cookies.get("access_token")
    if token and verify_token(token):
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return await render_with_user("login.html", request)


async def register_page(request: Request):
    require_registration_open()
    return await render_with_user("register.html", request)


async def register_user(request: Request,
                        first_name: str = Form(...),
                        last_name: str = Form(...),
                        email: str = Form(...),
                        password: str = Form(...),
                        confirm_password: str = Form(...),
                        security_answer: str = Form(...)):
    require_registration_open()

    if password != confirm_password or len(password) < MIN_PASSWORD_LENGTH:
        return await render_with_user("register.html", request, {
            "error": ("Passwords do not match" if password != confirm_password
                      else f"Use at least {MIN_PASSWORD_LENGTH} characters"),
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
    clear_auth_cookies(response)
    return response


async def forgot_password(request: Request):
    return await render_with_user("forgot_password.html", request)


async def reset_password(request: Request,
                         email: str = Form(...),
                         security_answer: str = Form(...),
                         new_password: str = Form(...),
                         confirm_password: str = Form(...)):
    def again(error: str):
        return render_with_user("forgot_password.html", request, {"error": error, "email": email})

    if new_password != confirm_password:
        return await again("Passwords do not match")
    if len(new_password) < MIN_PASSWORD_LENGTH:
        return await again(f"Use at least {MIN_PASSWORD_LENGTH} characters")
    try:
        response = await svc_reset_password(email, security_answer, new_password,
                                            client_ip=client_ip(request))
    except Exception:
        return await again("Unable to reach server. Please try again later.")

    if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        return await again("Too many attempts. Please wait a few minutes and try again.")
    if response.status_code == status.HTTP_400_BAD_REQUEST:
        return await again(response.json().get("detail", "Invalid request."))
    if response.status_code == status.HTTP_200_OK:
        # log the user in with the new password
        return await handle_authenticated_login(username=email, password=new_password, request=request)
    return await again("Server error. Try again later.")


async def reset_link_page(request: Request):
    # The token is in the URL fragment (/reset#token), which the browser never sends;
    # the page script copies it into the form.
    return await render_with_user("reset_link.html", request)


async def reset_link_submit(request: Request,
                            token: str = Form(""),
                            new_password: str = Form(...),
                            confirm_password: str = Form(...)):
    def again(error: str):
        # The token goes back into the form, so a typo does not need a new link.
        return render_with_user("reset_link.html", request, {"error": error, "token": token})

    if not token:
        return await again("Open the link from the owner again.")
    if new_password != confirm_password:
        return await again("Passwords do not match")
    if len(new_password) < MIN_PASSWORD_LENGTH:
        return await again(f"Use at least {MIN_PASSWORD_LENGTH} characters")

    response = await svc_use_reset_link(token, new_password, client_ip=client_ip(request))
    if response.status_code == status.HTTP_200_OK:
        rsp = redirect_with_toast("/dashboard", "Password set. Welcome back.", "success")
        set_auth_cookies(rsp, response.json()["access_token"])
        clear_active_budget_cookie(rsp)
        return rsp
    if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        return await again("Too many attempts. Please wait a few minutes and try again.")
    if response.status_code == status.HTTP_400_BAD_REQUEST:
        return await again(response.json().get("detail", "This link has expired or was already used."))
    return await again("Server error. Try again later.")


async def logout_all(request: Request):
    """Invalidate every session of this user, then clear this browser's cookies."""
    token = request.cookies.get("access_token")
    if token:
        await auth_logout_everywhere(token)
    response = RedirectResponse(
        url="/login", status_code=status.HTTP_303_SEE_OTHER)
    clear_auth_cookies(response)
    return response
