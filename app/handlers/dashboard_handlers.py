# app/handlers/dashboard_handlers.py
import logging
from datetime import datetime
from typing import Optional
from fastapi import Depends, Request, Form, Response, status
from fastapi.responses import RedirectResponse, HTMLResponse
from app.services.allocation_service import fetch_budget_overview
from app.services.budget_service import get_active_budget, get_all_budgets
from app.utils.active_budget import resolve_active_budget_id
from app.utils.templates import render_with_user
from app.utils.tokens import get_current_user
from app.services.auth_service import get_current_user as svc_get_current_user
from app.services.category_service import get_categories_by_type, get_categories_with_stats as svc_get_categories
from app.services.user_service import reset_password as svc_reset_password
from app.services.auth_service import login as svc_login
from app.utils.redirects import redirect_with_toast
from fastapi import HTTPException

logger = logging.getLogger(__name__)
HTMLResponse = HTMLResponse  # expose to router


async def profile(request: Request):
    token: str = get_current_user(request)
    user_response = await svc_get_current_user(token)
    if user_response.status_code != status.HTTP_200_OK:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    user = user_response.json()
    return await render_with_user("profile.html", request, {
        "token": token,
        "current_month": datetime.now().strftime('%B'),
        "user": user,
        "now": datetime.now().strftime("%Y-%m"),
    })


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


async def dashboard(
    request: Request,
    token: str = Depends(get_current_user),
    budget_id: Optional[int] = None
):
    # --------------------------------------------------
    # 1. Resolve authenticated user
    # --------------------------------------------------
    user_response = await svc_get_current_user(token=token)
    if user_response.status_code != status.HTTP_200_OK:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    user = user_response.json()

    # --------------------------------------------------
    # 2. Fetch ALL budgets for this user FIRST
    # --------------------------------------------------
    all_budgets_response = await get_all_budgets(token=token)

    if all_budgets_response.status_code != status.HTTP_200_OK:
        return redirect_with_toast(
            "/dashboard",
            "Unable to load budgets.",
            "error"
        )

    all_budgets = all_budgets_response.json()

    # If user truly has no budgets → correct message
    if not all_budgets:
        return redirect_with_toast(
            "/budgets/create",
            "Please create your first budget to continue.",
            "error"
        )

    # --------------------------------------------------
    # 3. Safely resolve active budget
    # --------------------------------------------------
    valid_budget_ids = {b["id"] for b in all_budgets}

    resolved_budget_id = None

    # Explicit query param wins if valid
    if budget_id and budget_id in valid_budget_ids:
        resolved_budget_id = budget_id
    else:
        # Fallback to cookie
        cookie_budget = request.cookies.get("active_budget_id")

        if cookie_budget:
            try:
                cookie_budget = int(cookie_budget)
                if cookie_budget in valid_budget_ids:
                    resolved_budget_id = cookie_budget
            except ValueError:
                pass  # corrupted cookie

    # Final fallback → first available budget
    if not resolved_budget_id:
        resolved_budget_id = all_budgets[0]["id"]

    # Get selected budget object directly
    active_budget = next(
        b for b in all_budgets if b["id"] == resolved_budget_id
    )

    # --------------------------------------------------
    # 4. Fetch dashboard data safely
    # --------------------------------------------------
    categories_response = await svc_get_categories(
        token=token,
        budget_id=resolved_budget_id
    )

    categories_with_stats = (
        categories_response.json()
        if categories_response.status_code == status.HTTP_200_OK
        else []
    )

    budget_allocations_response = await fetch_budget_overview(
        token=token,
        budget_id=resolved_budget_id
    )

    budget_allocations = (
        budget_allocations_response.json()
        if budget_allocations_response.status_code == status.HTTP_200_OK
        else {}
    )

    budget_categories_response = await get_categories_by_type(
        token=token,
        category_type=active_budget["type"]
    )

    budget_categories = (
        budget_categories_response.json()
        if budget_categories_response.status_code == status.HTTP_200_OK
        else []
    )
    print("Categories", categories_with_stats)
    # --------------------------------------------------
    # 5. Render template
    # --------------------------------------------------
    template_response = await render_with_user(
        "dashboard.html",
        request,
        {
            "categories_with_stats": categories_with_stats,
            "budget_allocations": budget_allocations,
            "budget_details": active_budget,
            "all_budgets": all_budgets,
            "budget_categories": budget_categories,
            "token": token,
            "current_month": datetime.now().strftime("%B"),
            "user": user,
            "now": datetime.now().strftime("%Y-%m"),
        }
    )

    # --------------------------------------------------
    # 6. Normalize / Repair Cookie
    # --------------------------------------------------
    existing_cookie = request.cookies.get("active_budget_id")

    if str(resolved_budget_id) != existing_cookie:
        template_response.set_cookie(
            key="active_budget_id",
            value=str(resolved_budget_id),
            httponly=True,
            samesite="lax"
        )

    return template_response


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
