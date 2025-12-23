# app/handlers/dashboard_handlers.py
import logging
from datetime import datetime
from fastapi import Depends, Request, Form, status
from fastapi.responses import RedirectResponse, HTMLResponse
from app.services.allocation_service import fetch_budget_overview
from app.services.budget_service import get_budget
from app.utils.templates import render_with_user
from app.utils.tokens import get_current_user
from app.services.auth_service import get_current_user as svc_get_current_user
from app.services.category_service import get_categories_with_stats as svc_get_categories
from app.services.user_service import reset_password as svc_reset_password
from app.services.auth_service import login as svc_login
from app.utils.redirects import redirect_with_toast
from fastapi import HTTPException

logger = logging.getLogger(__name__)
HTMLResponse = HTMLResponse  # expose to router


async def profile(request: Request):
    return await render_with_user("profile.html", request)


async def profile_update(request: Request,
                         first_name: str = Form(...),
                         last_name: str = Form(...),
                         email: str = Form(...),
                         security_answer: str = Form(...)):
    token = get_current_user(request)  # may raise redirect HTTPException

    from app.services.user_service import update_profile
    response = await update_profile(token, {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "security_answer": security_answer
    })

    if response.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED):
        return redirect_with_toast("/dashboard", "Profile updated successfully!", "success")

    if (response.status_code == status.HTTP_409_CONFLICT):
        return await render_with_user("profile.html", request, {
            "error": response.json().get('detail', 'Email already exists'),
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "security_answer": security_answer,
        })
    if (response.status_code == status.HTTP_404_NOT_FOUND):
        return await render_with_user("profile.html", request, {
            "error": response.json().get('detail', 'User not found'),
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "security_answer": security_answer,
        })
    try:
        error_detail = response.json().get("detail", "Update failed. Try again.")
    except Exception:
        error_detail = "Unexpected error. Please try again."

    return await render_with_user("profile.html", request, {
        "error": error_detail,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "security_answer": security_answer,
    })


async def dashboard(request: Request, token: str = Depends(get_current_user)):
    # get_current_user returns token string (same behaviour)
    user_response = await svc_get_current_user(token)
    if user_response.status_code != status.HTTP_200_OK:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    user = user_response.json()

    categories_response = await svc_get_categories(token)
    categories_with_stats = categories_response.json(
    ) if categories_response.status_code == status.HTTP_200_OK else []

    budget_response = await get_budget(token=token)
    budget = budget_response.json(
    ) if budget_response.status_code == status.HTTP_200_OK else None

    budget_allocations_response = await fetch_budget_overview(token=token,
                                                              budget_id=budget["id"])
    budget_allocations = budget_allocations_response.json(
    ) if budget_allocations_response.status_code == status.HTTP_200_OK else {}

    return await render_with_user("dashboard.html", request, {
        "categories_with_stats": categories_with_stats,
        "budget_allocations": budget_allocations,
        "budget_details": budget,
        "token": token,
        "current_month": datetime.now().strftime('%B'),
        "user": user,
        "now": datetime.now().strftime("%Y-%m"),
    })


async def forgot_password(request: Request):
    return await render_with_user("forgot_password.html", request)


async def reset_password(request: Request,
                         email: str = Form(...),
                         security_answer: str = Form(...),
                         new_password: str = Form(...)):
    try:
        from app.services.user_service import reset_password as svc_reset
        response = await svc_reset(email, security_answer, new_password)
    except Exception:
        # keep original message
        return await render_with_user("forgot_password.html", request, {
            "error": "Unable to reach server. Please try again later."
        })

    if response.status_code == status.HTTP_404_NOT_FOUND:
        return await render_with_user("forgot_password.html", request, {"error": "User not found."})
    if response.status_code == status.HTTP_400_BAD_REQUEST:
        return await render_with_user("forgot_password.html", request, {"error": response.json().get("detail", "Invalid request.")})
    if response.status_code >= 500:
        return await render_with_user("forgot_password.html", request, {"error": "Server error. Try again later."})
    if response.status_code == status.HTTP_200_OK:
        # login the user with new password
        login_resp = await svc_login(email, new_password)
        if login_resp.status_code == status.HTTP_200_OK:
            token_data = login_resp.json()
            access_token = token_data["access_token"]
            rsp = RedirectResponse(
                url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
            rsp.set_cookie(key="access_token", value=access_token,
                           httponly=True, max_age=86400)
            rsp.set_cookie(key="show_menu", value="1",
                           httponly=False, max_age=86400)
            return rsp

    return await render_with_user("forgot_password.html", request, {
        "error": f"Unexpected response: {response.status_code}"
    })
