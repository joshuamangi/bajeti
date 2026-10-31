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
from app.services.user_service import change_password as svc_change_password, update_profile
from core.rate_limit import client_ip
from app.utils.cookies import set_active_budget_cookie, set_auth_cookies
from schema.user import MIN_PASSWORD_LENGTH
from app.utils.redirects import redirect_with_toast
from app.utils.target_totals import target_totals
from app.utils.home_view import home_view, page_data
from app.services.recurring_service import fetch_due
from app.services.payment_service import fetch_count as fetch_payment_count
from app.services import api_token_service
from app.config import settings
from fastapi import HTTPException

logger = logging.getLogger(__name__)
HTMLResponse = HTMLResponse  # expose to router


async def profile(request: Request):
    return await _render_profile(request)


async def _render_profile(request: Request, new_token: Optional[dict] = None):
    token: str = get_current_user(request)
    user_response = await svc_get_current_user(token)
    if user_response.status_code != status.HTTP_200_OK:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    user = user_response.json()
    tokens_response = await api_token_service.fetch_tokens(token)
    phone_tokens = tokens_response.json() if tokens_response.status_code == status.HTTP_200_OK else []
    response = await render_with_user("profile.html", request, {
        "active_tab": "more",
        "token": token,
        "current_month": datetime.now().strftime('%B'),
        "user": user,
        "now": datetime.now().strftime("%Y-%m"),
        "phone_tokens": phone_tokens,
        "new_token": new_token,
        "shortcut_url": settings.SHORTCUT_INSTALL_URL,
    })
    if new_token:
        # The new phone token is in this page only: keep it out of every cache.
        response.headers["Cache-Control"] = "no-store"
    return response


async def create_phone_token(request: Request, name: str = Form("iPhone")):
    """Shown once on the page this returns, never put in a redirect or a cookie."""
    token = get_current_user(request)
    resp = await api_token_service.create_token(token, (name or "iPhone").strip()[:40] or "iPhone")
    if resp.status_code != status.HTTP_201_CREATED:
        try:
            detail = resp.json().get("detail", "Could not create a token.")
        except ValueError:
            detail = "Could not create a token."
        return redirect_with_toast("/profile", detail if isinstance(detail, str) else "Check the name.", "error")
    return await _render_profile(request, new_token=resp.json())


async def revoke_phone_token(request: Request, token_id: int):
    token = get_current_user(request)
    resp = await api_token_service.revoke_token(token, token_id)
    if resp.status_code == status.HTTP_204_NO_CONTENT:
        return redirect_with_toast("/profile", "Token revoked. That phone can no longer send payments.", "warning")
    return redirect_with_toast("/profile", "Could not revoke that token.", "error")


async def profile_update(request: Request,
                         first_name: str = Form(...),
                         last_name: str = Form(...),
                         email: str = Form(...)):
    token = get_current_user(request)  # may raise redirect HTTPException

    response = await update_profile(token, {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
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


async def security_question_update(request: Request,
                                   security_answer: str = Form(...),
                                   current_password: str = Form(...)):
    # The answer can reset the password, so setting it needs the password too.
    token = get_current_user(request)
    response = await update_profile(token, {
        "security_answer": security_answer,
        "current_password": current_password,
    })
    if response.status_code == status.HTTP_200_OK:
        return redirect_with_toast("/profile", "Security question saved", "success")
    if response.status_code == status.HTTP_400_BAD_REQUEST:
        return redirect_with_toast("/profile", "Current password is incorrect", "error")
    return redirect_with_toast("/profile", "Could not save. Try again.", "error")


async def change_password_page(request: Request, token: str = Depends(get_current_user)):
    return await render_with_user("change_password.html", request, {"active_tab": "more"})


async def change_password(request: Request,
                          current_password: str = Form(...),
                          new_password: str = Form(...),
                          confirm_password: str = Form(...)):
    token = get_current_user(request)

    def again(error: str):
        return render_with_user("change_password.html", request, {"active_tab": "more", "error": error})

    if new_password != confirm_password:
        return await again("New passwords do not match")
    if len(new_password) < MIN_PASSWORD_LENGTH:
        return await again(f"Use at least {MIN_PASSWORD_LENGTH} characters")

    response = await svc_change_password(token, current_password, new_password,
                                         client_ip=client_ip(request))
    if response.status_code == status.HTTP_200_OK:
        rsp = redirect_with_toast("/profile", "Password changed. Other devices are signed out.", "success")
        set_auth_cookies(rsp, response.json()["access_token"])
        return rsp
    if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        return await again("Too many attempts. Please wait a few minutes and try again.")
    if response.status_code == status.HTTP_400_BAD_REQUEST:
        return await again("Current password is incorrect")
    return await again("Could not change the password. Try again.")


def pick_budget_id(all_budgets: list, budget_id: Optional[int], cookie_budget: Optional[str]) -> int:
    """A valid ?budget_id wins, then the cookie (this session's pick), then the default budget
    (set on the Budgets screen), then the first budget. The login clears the cookie."""
    valid_budget_ids = {b["id"] for b in all_budgets}
    if budget_id and budget_id in valid_budget_ids:
        return budget_id
    try:
        if cookie_budget and int(cookie_budget) in valid_budget_ids:
            return int(cookie_budget)
    except ValueError:
        pass  # corrupted cookie
    return next((b for b in all_budgets if b.get("is_default")), all_budgets[0])["id"]


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
    resolved_budget_id = pick_budget_id(all_budgets, budget_id, request.cookies.get("active_budget_id"))

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

    # Ask-first recurring items due today or overdue (auto items are recorded by this call).
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

