# app/handlers/analytics_handlers.py
import re
from datetime import datetime
from typing import Optional

from fastapi import Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.handlers.dashboard_handlers import load_app_context
from app.services import analytics_service
from app.utils.cookies import set_active_budget_cookie
from app.utils.templates import render_with_user
from app.utils.tokens import get_current_user

HTMLResponse = HTMLResponse  # expose to router
MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def this_month() -> str:
    return datetime.now().strftime("%Y-%m")


async def _render(request: Request, token: str, view: str, fetch, budget_id: Optional[int] = None,
                  extra: Optional[dict] = None):
    """Shell context for the active budget, then one API call for the view.
    fetch(budget_id) returns the API response. A failed call shows the error state."""
    context, active_id = await load_app_context(request, token, budget_id)
    if not isinstance(context, dict):
        return context
    context.update({"active_tab": "analytics", "view": view, "this_month": this_month(), **(extra or {})})
    if active_id:
        response = await fetch(active_id)
        context["data"] = response.json() if response.status_code == status.HTTP_200_OK else None
        context["error_code"] = None if context["data"] else response.status_code
    rendered = await render_with_user("analytics.html", request, context)
    if active_id and str(active_id) != request.cookies.get("active_budget_id"):
        set_active_budget_cookie(rendered, active_id)
    return rendered


async def analytics_home(request: Request):
    return RedirectResponse(url=f"/analytics/{this_month()}", status_code=status.HTTP_303_SEE_OTHER)


async def analytics_month(request: Request, month: str, token: str = Depends(get_current_user),
                          budget_id: Optional[int] = None):
    if not MONTH.match(month) or month > this_month():
        return RedirectResponse(url=f"/analytics/{this_month()}", status_code=status.HTTP_303_SEE_OTHER)
    return await _render(request, token, "month",
                         lambda bid: analytics_service.fetch_month(token, bid, month), budget_id,
                         {"month": month})


async def analytics_trends(request: Request, token: str = Depends(get_current_user),
                           budget_id: Optional[int] = None):
    return await _render(request, token, "trends",
                         lambda bid: analytics_service.fetch_trends(token, bid, this_month()), budget_id)


async def analytics_year(request: Request, year: Optional[int] = None, token: str = Depends(get_current_user),
                         budget_id: Optional[int] = None):
    current = int(this_month()[:4])
    if year is None or not 2000 <= year <= current:
        return RedirectResponse(url=f"/analytics/year/{current}", status_code=status.HTTP_303_SEE_OTHER)
    return await _render(request, token, "year",
                         lambda bid: analytics_service.fetch_year(token, bid, year), budget_id, {"year": year})


async def analytics_category(request: Request, month: str, category_id: int,
                             token: str = Depends(get_current_user)):
    if not MONTH.match(month) or month > this_month():
        return RedirectResponse(url=f"/analytics/{this_month()}", status_code=status.HTTP_303_SEE_OTHER)
    response = await analytics_service.fetch_category(token, category_id, month)
    if response.status_code != status.HTTP_200_OK:
        return RedirectResponse(url=f"/analytics/{month}", status_code=status.HTTP_303_SEE_OTHER)
    data = response.json()
    # Opening a category from another budget makes that budget active.
    return await _render(request, token, "category",
                         lambda bid: analytics_service.fetch_category(token, category_id, month),
                         data["budget"]["id"], {"month": month})
