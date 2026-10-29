# app/handlers/dashboard_handlers.py
import logging
from datetime import date, datetime
from typing import Optional
from fastapi import Depends, Request, Form, Response, status
from fastapi.responses import RedirectResponse, HTMLResponse
from app.services.allocation_service import fetch_budget_overview
from app.services.budget_service import get_active_budget, get_all_budgets
from app.utils.active_budget import resolve_active_budget_id
from app.utils.templates import render_with_user
from app.utils.tokens import get_current_user
from app.services.auth_service import get_current_user as svc_get_current_user
from app.services.category_service import get_categories_with_stats as svc_get_categories
from app.services.user_service import reset_password as svc_reset_password
from app.services.auth_service import login as svc_login
from core.rate_limit import client_ip
from app.utils.cookies import set_active_budget_cookie, set_auth_cookies
from app.utils.redirects import redirect_with_toast
from app.utils.target_totals import target_totals
from app.utils.home_view import home_view, page_data
from app.services.recurring_service import fetch_due
from app.services.payment_service import fetch_count as fetch_payment_count
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
        "active_tab": "more",
        "token": token,
        "current_month": datetime.now().strftime('%B'),
        "user": user,
        "now": datetime.now().strftime("%Y-%m"),
    })


async def profile_update(request: Request,
                         first_name: str = Form(...),
                         last_name: str = Form(...),
                         email: str = Form(...),
                         security_answer: str = Form("")):
    # A blank answer keeps the current one (it is stored hashed and cannot be shown).
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

    if response.status_code in (status.HTTP_409_CONFLICT, status.HTTP_404_NOT_FOUND):
        fallback = "Email already exists" if response.status_code == status.HTTP_409_CONFLICT else "User not found"
        return redirect_with_toast("/profile", response.json().get("detail", fallback), "error")
    try:
        error_detail = response.json().get("detail", "Update failed. Try again.")
    except Exception:
        error_detail = "Unexpected error. Please try again."
    return redirect_with_toast("/profile", str(error_detail), "error")


async def load_app_context(request: Request, token: str, budget_id: Optional[int] = None):
    """Data every signed-in screen needs: the user, all budgets and the active budget with its
    category stats for this month. Returns (context, active budget id) or a Response to send."""
    # 1. Resolve authenticated user
    user_response = await svc_get_current_user(token=token)
    if user_response.status_code != status.HTTP_200_OK:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER), None

    user = user_response.json()
    month = datetime.now().strftime("%Y-%m")

    # 2. Fetch ALL budgets for this user FIRST
    all_budgets_response = await get_all_budgets(token=token)

    if all_budgets_response.status_code != status.HTTP_200_OK:
        return redirect_with_toast(
            "/more",
            "Unable to load budgets.",
            "error"
        ), None

    all_budgets = all_budgets_response.json()

    context = {
        "user": user,
        "all_budgets": all_budgets,
        "current_month": datetime.now().strftime("%B"),
        "now": month,
    }

    # No budgets yet: the screens show the "Create a budget" empty state.
    if not all_budgets:
        context.update({
            "budget_details": None,
            "home": None,
            "budget_allocations": {},
            "target_totals": target_totals([]),
            "page_data": {"budget": None, "budgets": [], "categories": [], "month": month},
        })
        return context, None

    # 3. Safely resolve active budget
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

    # 4. Fetch the active budget's data safely
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

    home = home_view(active_budget, categories_with_stats, date.today())
    data = page_data(active_budget, all_budgets, home, month)
    # Allocation ids, so the Budgets screen can remove an allocation.
    allocation_ids = {row["category_id"]: row["allocation_id"]
                      for row in budget_allocations.get("allocations", [])}
    for category in data["categories"]:
        category["allocation_id"] = allocation_ids.get(category["id"])

    # Ask-first recurring items due within 5 days (auto items are recorded by this call).
    due_response = await fetch_due(token=token, budget_id=resolved_budget_id)
    due = due_response.json() if due_response.status_code == status.HTTP_200_OK else []
    data["due"] = due

    count_response = await fetch_payment_count(token=token)
    pending_count = count_response.json().get("pending", 0) if count_response.status_code == status.HTTP_200_OK else 0

    context.update({
        "due": due,
        "pending_count": pending_count,
        "attention_count": len(due) + pending_count,
        "home": home,
        "page_data": data,
        "categories_with_stats": categories_with_stats,
        "target_totals": target_totals(categories_with_stats),
        "budget_allocations": budget_allocations,
        "budget_details": active_budget,
    })
    return context, resolved_budget_id


async def render_app_page(template: str, tab: str, request: Request, token: str,
                          budget_id: Optional[int] = None, extra: Optional[dict] = None, extra_async=None):
    """Render a signed-in page. extra_async(context, active budget id) can add data per page."""
    context, resolved_budget_id = await load_app_context(request, token, budget_id)
    if not isinstance(context, dict):
        return context
    context["active_tab"] = tab
    if extra:
        context.update(extra)
    if extra_async:
        context.update(await extra_async(context, resolved_budget_id))
    template_response = await render_with_user(template, request, context)
    # Normalize / Repair Cookie
    if resolved_budget_id and str(resolved_budget_id) != request.cookies.get("active_budget_id"):
        set_active_budget_cookie(template_response, resolved_budget_id)
    return template_response


async def dashboard(
    request: Request,
    token: str = Depends(get_current_user),
    budget_id: Optional[int] = None
):
    return await render_app_page("dashboard.html", "home", request, token, budget_id)


async def budgets_page(
    request: Request,
    token: str = Depends(get_current_user),
    budget_id: Optional[int] = None
):
    return await render_app_page("budgets.html", "budgets", request, token, budget_id)


async def more_page(request: Request, token: str = Depends(get_current_user)):
    return await render_app_page("more.html", "more", request, token)


async def forgot_password(request: Request):
    return await render_with_user("forgot_password.html", request)


async def reset_password(request: Request,
                         email: str = Form(...),
                         security_answer: str = Form(...),
                         new_password: str = Form(...)):
    try:
        from app.services.user_service import reset_password as svc_reset
        response = await svc_reset(email, security_answer, new_password,
                                   client_ip=client_ip(request))
    except Exception:
        # keep original message
        return await render_with_user("forgot_password.html", request, {
            "error": "Unable to reach server. Please try again later."
        })

    if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        return await render_with_user("forgot_password.html", request, {
            "error": "Too many attempts. Please wait a few minutes and try again."})
    if response.status_code == status.HTTP_400_BAD_REQUEST:
        return await render_with_user("forgot_password.html", request, {"error": response.json().get("detail", "Invalid request.")})
    if response.status_code >= 500:
        return await render_with_user("forgot_password.html", request, {"error": "Server error. Try again later."})
    if response.status_code == status.HTTP_200_OK:
        # login the user with new password
        login_resp = await svc_login(email, new_password, client_ip=client_ip(request))
        if login_resp.status_code == status.HTTP_200_OK:
            token_data = login_resp.json()
            access_token = token_data["access_token"]
            rsp = RedirectResponse(
                url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
            set_auth_cookies(rsp, access_token)
            return rsp

    return await render_with_user("forgot_password.html", request, {
        "error": f"Unexpected response: {response.status_code}"
    })
